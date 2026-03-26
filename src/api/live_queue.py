"""Persistent server-side queue for the Live Payment Monitor.

Builds a curated 10,000-event queue from pre-scored seed data in Postgres
and emits events at a configurable TPS rate via an async broadcast channel.

Key properties:
  - Survives browser refresh / different user logins (server-side state)
  - Multiple SSE clients share the same event stream (broadcast)
  - Curated geographic + specialty diversity, not ORDER BY RANDOM()
  - Queue loops forever: when exhausted, reshuffles and replays

Lifecycle: start_queue() is triggered lazily by the live monitor routes;
stop_queue() is called during API shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from psycopg.rows import dict_row

from src.api import deps as _deps

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QUEUE_SIZE = 10_000

# Target distribution
HIGH_RISK_COUNT = 1_500  # 15%
REVIEW_COUNT = 3_500  # 35%
STABLE_COUNT = 5_000  # 50%

# Default events per second
DEFAULT_TPS = 2.0

# How many top states to pull from for geographic diversity
TOP_STATES_COUNT = 20

# ---------------------------------------------------------------------------
# Pre-scored event (cached — no re-scoring needed at emit time)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueueEvent:
    """A fully pre-scored claim ready for SSE emission."""

    npi: str
    provider_name: str
    state: str
    city: str
    hcpcs_code: str
    hcpcs_desc: str
    submitted_charge: float
    provider_type: str
    risk_score: int
    legitimacy_score: int
    case_label: str  # "high_risk" | "review" | "stable"
    anomaly_score: float | None
    signals: list[str]
    scoring_latency_ms: float


# ---------------------------------------------------------------------------
# SQL — curated selection queries (NOT random)
# ---------------------------------------------------------------------------

_CASES_BY_BAND_SQL = """
WITH ranked AS (
    SELECT case_id, npi,
           COALESCE(provider_last_org_name, '') ||
               CASE WHEN provider_first_name IS NOT NULL
                    THEN ', ' || provider_first_name
                    ELSE '' END AS provider_name,
           provider_state AS state,
           provider_city AS city,
           hcpcs_cd, hcpcs_desc, place_of_service, provider_type,
           avg_submitted_charge, tot_srvcs, tot_benes,
           present_in_2025_enrollment_file, present_in_2026_revocation_file,
           medicare_participating_ind, provider_total_benes,
           peer_scope, peer_case_count, peer_avg_tot_srvcs,
           service_volume_peer_z, services_per_bene_peer_z,
           submitted_to_allowed_peer_z, payment_peer_z,
           seed_risk_score, seed_legitimacy_score, seed_case_label,
           seed_risk_reasons,
           ROW_NUMBER() OVER (
               PARTITION BY provider_state
               ORDER BY npi, case_id
           ) AS rn
    FROM provider_service_cases
    WHERE {band_filter}
      AND provider_state IS NOT NULL
      AND provider_state IN ({state_placeholders})
)
SELECT * FROM ranked
WHERE rn <= %(per_state_limit)s
ORDER BY state, rn
"""

_TOP_STATES_SQL = """
SELECT provider_state, COUNT(*) AS cnt
FROM provider_service_cases
WHERE provider_state IS NOT NULL
GROUP BY provider_state
ORDER BY cnt DESC
LIMIT %(limit)s
"""

# ---------------------------------------------------------------------------
# Band filter helpers
# ---------------------------------------------------------------------------


def _high_risk_filter() -> str:
    """SQL WHERE clause fragment for high_risk seed cases."""
    return "seed_case_label = 'high_risk'"


def _stable_filter() -> str:
    """SQL WHERE clause fragment for stable seed cases."""
    return "seed_case_label = 'stable'"


def _review_filter() -> str:
    """SQL WHERE clause fragment for review seed cases."""
    return "seed_case_label = 'review'"


# ---------------------------------------------------------------------------
# Queue Manager singleton
# ---------------------------------------------------------------------------


@dataclass
class QueueManager:
    """Server-side persistent queue that broadcasts pre-scored events."""

    queue: list[QueueEvent] = field(default_factory=list)
    position: int = 0
    tps: float = DEFAULT_TPS
    running: bool = False
    ready: bool = False
    total_emitted: int = 0

    # Broadcast: connected clients listen via asyncio.Queue
    _subscribers: list[asyncio.Queue[str]] = field(default_factory=list)
    _task: asyncio.Task | None = field(default=None, repr=False)  # type: ignore[type-arg]
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # Stats
    build_time_s: float = 0.0
    queue_actual_counts: dict[str, int] = field(default_factory=dict)

    def subscribe(self) -> asyncio.Queue[str]:
        """Add a new subscriber. Returns a Queue that receives SSE strings."""
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        logger.info("live queue: subscriber added (total=%d)", len(self._subscribers))
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        """Remove a subscriber."""
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass
        logger.info("live queue: subscriber removed (total=%d)", len(self._subscribers))

    async def _broadcast(self, data: str) -> None:
        """Send an SSE event string to all subscribers."""
        dead: list[asyncio.Queue[str]] = []
        for q in self._subscribers:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                # Slow consumer — drop oldest event and push new one
                try:
                    q.get_nowait()
                    q.put_nowait(data)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    async def build_queue(self) -> None:
        """Query the DB and build the curated 10K queue."""
        if _deps.pool is None:
            logger.error("live queue: DB pool not initialized")
            return

        start = time.monotonic()
        logger.info("live queue: building curated %d-event queue...", QUEUE_SIZE)

        async with _deps.pool.connection() as conn:
            # 1. Get top states for geographic diversity
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(_TOP_STATES_SQL, {"limit": TOP_STATES_COUNT})
                state_rows = await cur.fetchall()
            top_states = [r["provider_state"] for r in state_rows]
            logger.info("live queue: top %d states: %s", len(top_states), top_states)

            # 2. Fetch candidates for each band with state distribution
            high_risk_rows = await self._fetch_band(
                conn, top_states, _high_risk_filter(), HIGH_RISK_COUNT * 2
            )
            review_rows = await self._fetch_band(
                conn, top_states, _review_filter(), REVIEW_COUNT * 2
            )
            stable_rows = await self._fetch_band(
                conn, top_states, _stable_filter(), STABLE_COUNT * 2
            )

            logger.info(
                "live queue: fetched candidates — high_risk=%d, review=%d, stable=%d",
                len(high_risk_rows),
                len(review_rows),
                len(stable_rows),
            )

            # 3. Convert pre-scored seed rows into queue events.
            high_risk_evts = self._diverse_sample(
                [self._event_from_seed_row(row) for row in high_risk_rows],
                HIGH_RISK_COUNT,
            )
            review_evts = self._diverse_sample(
                [self._event_from_seed_row(row) for row in review_rows],
                REVIEW_COUNT,
            )
            stable_evts = self._diverse_sample(
                [self._event_from_seed_row(row) for row in stable_rows],
                STABLE_COUNT,
            )

            # 4. Interleave for natural-looking stream
            self.queue = self._interleave(high_risk_evts, review_evts, stable_evts)
            self.position = 0
            self.queue_actual_counts = {
                "high_risk": len(high_risk_evts),
                "review": len(review_evts),
                "stable": len(stable_evts),
                "total": len(self.queue),
            }

        self.build_time_s = time.monotonic() - start
        self.ready = True
        logger.info(
            "live queue: built %d events in %.1fs — %s",
            len(self.queue),
            self.build_time_s,
            self.queue_actual_counts,
        )

    async def _fetch_band(
        self,
        conn,  # type: ignore[type-arg]
        top_states: list[str],
        band_filter: str,
        total_limit: int,
    ) -> list[dict]:
        """Fetch candidate rows for a risk band, spread across states."""
        per_state = max(total_limit // len(top_states), 10)
        state_placeholders = ", ".join(f"%(s{i})s" for i in range(len(top_states)))
        params: dict = {f"s{i}": s for i, s in enumerate(top_states)}
        params["per_state_limit"] = per_state

        sql = _CASES_BY_BAND_SQL.format(
            band_filter=band_filter,
            state_placeholders=state_placeholders,
        )
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _event_from_seed_row(row: dict) -> QueueEvent:
        """Convert a pre-scored DB row into a queue event."""
        signals = QueueManager._parse_seed_reasons(row.get("seed_risk_reasons"))
        return QueueEvent(
            npi=row.get("npi", ""),
            provider_name=row.get("provider_name") or "Unknown",
            state=row.get("state") or "Unknown",
            city=row.get("city") or "",
            hcpcs_code=row.get("hcpcs_cd") or "",
            hcpcs_desc=row.get("hcpcs_desc") or "",
            submitted_charge=float(row.get("avg_submitted_charge") or 0),
            provider_type=row.get("provider_type") or "",
            risk_score=int(row.get("seed_risk_score") or 0),
            legitimacy_score=int(row.get("seed_legitimacy_score") or 0),
            case_label=row.get("seed_case_label") or "review",
            anomaly_score=None,
            signals=signals,
            scoring_latency_ms=0.0,
        )

    @staticmethod
    def _parse_seed_reasons(raw: str | None) -> list[str]:
        """Parse pipe-delimited seed risk reasons into a clean list."""
        if not raw:
            return []
        return [part.strip() for part in raw.split("|") if part.strip()]

    @staticmethod
    def _diverse_sample(events: list[QueueEvent], target: int) -> list[QueueEvent]:
        """Sample up to `target` events with state + provider_type diversity."""
        if len(events) <= target:
            return list(events)

        # Round-robin by state to ensure geographic spread
        by_state: dict[str, list[QueueEvent]] = defaultdict(list)
        for e in events:
            by_state[e.state].append(e)

        # Shuffle within each state bucket
        for evts in by_state.values():
            random.shuffle(evts)

        result: list[QueueEvent] = []
        seen_npis: set[str] = set()
        states = list(by_state.keys())
        random.shuffle(states)

        # Round-robin across states
        idx = 0
        while len(result) < target:
            added_this_round = False
            for state in states:
                bucket = by_state[state]
                while idx < len(bucket) and bucket[idx].npi in seen_npis:
                    idx += 1
                # Find next unseen NPI in this state
                for i in range(len(bucket)):
                    if bucket[i].npi not in seen_npis:
                        result.append(bucket[i])
                        seen_npis.add(bucket[i].npi)
                        bucket.pop(i)
                        added_this_round = True
                        break
                if len(result) >= target:
                    break
            if not added_this_round:
                break
            idx = 0

        return result[:target]

    @staticmethod
    def _interleave(
        high_risk: list[QueueEvent],
        review: list[QueueEvent],
        stable: list[QueueEvent],
    ) -> list[QueueEvent]:
        """Interleave events so ~every 7th is high_risk, stream looks natural.

        Strategy: build a sequence where stable events form the background,
        review events are mixed in at 35% rate, and high_risk events appear
        roughly every 7th position.
        """
        result: list[QueueEvent] = []

        # Create indexed iterators
        hr = list(high_risk)
        rv = list(review)
        st = list(stable)
        random.shuffle(hr)
        random.shuffle(rv)
        random.shuffle(st)

        hr_idx = rv_idx = st_idx = 0
        total = len(hr) + len(rv) + len(st)

        for i in range(total):
            # Every 7th → high_risk (if available)
            if (i + 1) % 7 == 0 and hr_idx < len(hr):
                result.append(hr[hr_idx])
                hr_idx += 1
            # Every 3rd of remaining → review
            elif (i + 1) % 3 == 0 and rv_idx < len(rv):
                result.append(rv[rv_idx])
                rv_idx += 1
            # Otherwise → stable
            elif st_idx < len(st):
                result.append(st[st_idx])
                st_idx += 1
            # Drain remaining from any bucket
            elif rv_idx < len(rv):
                result.append(rv[rv_idx])
                rv_idx += 1
            elif hr_idx < len(hr):
                result.append(hr[hr_idx])
                hr_idx += 1

        return result

    async def _emit_loop(self) -> None:
        """Main loop: emits events at configured TPS, loops queue forever."""
        logger.info("live queue: emit loop started (tps=%.1f)", self.tps)
        while self.running:
            if not self.queue:
                await asyncio.sleep(1.0)
                continue

            evt = self.queue[self.position]
            self.position = (self.position + 1) % len(self.queue)
            self.total_emitted += 1

            payload = {
                "event_id": f"evt_{self.total_emitted:06d}",
                "timestamp": datetime.now(UTC).isoformat(),
                "npi": evt.npi,
                "provider_name": evt.provider_name,
                "state": evt.state,
                "city": evt.city,
                "hcpcs_code": evt.hcpcs_code,
                "hcpcs_desc": evt.hcpcs_desc,
                "submitted_charge": evt.submitted_charge,
                "provider_type": evt.provider_type,
                "risk_score": evt.risk_score,
                "legitimacy_score": evt.legitimacy_score,
                "case_label": evt.case_label,
                "anomaly_score": evt.anomaly_score,
                "signals": evt.signals,
                "scoring_latency_ms": evt.scoring_latency_ms,
            }

            sse_data = f"data: {json.dumps(payload)}\n\n"
            await self._broadcast(sse_data)

            await asyncio.sleep(1.0 / self.tps)

    async def start(self) -> None:
        """Build queue and start the emit loop as a background task."""
        async with self._lock:
            if self.running:
                logger.warning("live queue: already running")
                return
            self.running = True
            self.ready = False
            try:
                await self.build_queue()
            except asyncio.CancelledError:
                self.running = False
                self.ready = False
                self.queue = []
                self.position = 0
                self.queue_actual_counts = {}
                logger.info("live queue: startup cancelled")
                raise
            except Exception:
                self.running = False
                self.ready = False
                self.queue = []
                self.position = 0
                self.queue_actual_counts = {}
                logger.exception("live queue: startup failed")
                raise
            self._task = asyncio.create_task(self._emit_loop())
            logger.info("live queue: started")

    async def stop(self) -> None:
        """Stop the emit loop."""
        async with self._lock:
            self.running = False
            self.ready = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None
            logger.info("live queue: stopped")

    def set_tps(self, tps: float) -> None:
        """Update the emission rate (takes effect on next sleep cycle)."""
        self.tps = max(0.1, min(tps, 20.0))
        logger.info("live queue: TPS set to %.1f", self.tps)

    def status(self) -> dict:
        """Return current queue status for the /live/status endpoint."""
        return {
            "running": self.running,
            "ready": self.ready,
            "queue_size": len(self.queue),
            "position": self.position,
            "total_emitted": self.total_emitted,
            "tps": self.tps,
            "subscribers": len(self._subscribers),
            "build_time_s": round(self.build_time_s, 1),
            "distribution": self.queue_actual_counts,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

queue_manager = QueueManager()


async def start_queue() -> None:
    """Start the queue on demand from the live monitor routes."""
    await queue_manager.start()


async def stop_queue() -> None:
    """Called from FastAPI lifespan on shutdown."""
    await queue_manager.stop()
