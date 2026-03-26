"""Continuous server-side stream for the Live Payment Monitor.

Streams small batches of pre-scored seed data from Postgres and broadcasts
them to all connected SSE clients at a configurable TPS rate.

Key properties:
  - Survives browser refresh / different user logins (server-side state)
  - Multiple SSE clients share the same event stream (broadcast)
  - No large prebuilt in-memory queue at startup
  - Small rolling batches keep API load predictable

Lifecycle: start_queue() is triggered lazily by the live monitor routes;
stop_queue() is called during API shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from psycopg.rows import dict_row

from src.api import deps as _deps

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Small rolling batch size. Keeps the live stream responsive without
# prebuilding a large queue or re-scoring rows on demand.
BATCH_TARGETS = {
    "high_risk": 4,
    "review": 8,
    "stable": 12,
}

# Default events per second
DEFAULT_TPS = 2.0

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
# SQL — rolling seed-backed selection queries
# ---------------------------------------------------------------------------

_CASES_AFTER_SQL = """
SELECT case_id, npi,
       COALESCE(provider_last_org_name, '') ||
           CASE WHEN provider_first_name IS NOT NULL
                THEN ', ' || provider_first_name
                ELSE '' END AS provider_name,
       provider_state AS state,
       provider_city AS city,
       hcpcs_cd, hcpcs_desc, place_of_service, provider_type,
       avg_submitted_charge,
       seed_risk_score, seed_legitimacy_score, seed_case_label,
       seed_risk_reasons
FROM provider_service_cases
WHERE seed_case_label = %(label)s
  AND case_id > %(after_case_id)s
ORDER BY case_id
LIMIT %(limit)s
"""


# ---------------------------------------------------------------------------
# Queue Manager singleton
# ---------------------------------------------------------------------------


@dataclass
class QueueManager:
    """Server-side continuous stream that broadcasts pre-scored events."""

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
    _band_after_case_id: dict[str, int] = field(
        default_factory=lambda: {label: 0 for label in BATCH_TARGETS}
    )

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
        if not self._subscribers:
            self.ready = False
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

    @staticmethod
    def _get_db_pool():
        """Prefer the readonly pool for streaming when available."""
        return _deps.readonly_pool or _deps.pool

    async def _fetch_band_rows(
        self,
        conn,  # type: ignore[type-arg]
        label: str,
        limit: int,
    ) -> list[dict]:
        """Fetch a rolling batch for a single seed label using keyset pagination."""
        after_case_id = self._band_after_case_id.get(label, 0)
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                _CASES_AFTER_SQL,
                {
                    "label": label,
                    "after_case_id": after_case_id,
                    "limit": limit,
                },
            )
            rows = await cur.fetchall()
            if not rows and after_case_id > 0:
                await cur.execute(
                    _CASES_AFTER_SQL,
                    {
                        "label": label,
                        "after_case_id": 0,
                        "limit": limit,
                    },
                )
                rows = await cur.fetchall()

        fetched = [dict(r) for r in rows]
        if fetched:
            self._band_after_case_id[label] = int(fetched[-1]["case_id"])
        else:
            self._band_after_case_id[label] = 0
        return fetched

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
    def _interleave(
        high_risk: list[QueueEvent],
        review: list[QueueEvent],
        stable: list[QueueEvent],
    ) -> list[QueueEvent]:
        """Interleave events so the stream feels mixed rather than banded."""
        result: list[QueueEvent] = []
        hr = list(high_risk)
        rv = list(review)
        st = list(stable)

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

    async def _load_next_batch(self) -> bool:
        """Load the next rolling batch from Postgres."""
        db_pool = self._get_db_pool()
        if db_pool is None:
            logger.error("live queue: DB pool not initialized")
            return False

        start = time.monotonic()
        async with db_pool.connection() as conn:
            high_risk_rows = await self._fetch_band_rows(
                conn, "high_risk", BATCH_TARGETS["high_risk"]
            )
            review_rows = await self._fetch_band_rows(
                conn, "review", BATCH_TARGETS["review"]
            )
            stable_rows = await self._fetch_band_rows(
                conn, "stable", BATCH_TARGETS["stable"]
            )

        high_risk_evts = [self._event_from_seed_row(row) for row in high_risk_rows]
        review_evts = [self._event_from_seed_row(row) for row in review_rows]
        stable_evts = [self._event_from_seed_row(row) for row in stable_rows]

        self.queue = self._interleave(high_risk_evts, review_evts, stable_evts)
        self.position = 0
        self.queue_actual_counts = {
            "high_risk": len(high_risk_evts),
            "review": len(review_evts),
            "stable": len(stable_evts),
            "total": len(self.queue),
        }
        self.build_time_s = time.monotonic() - start
        self.ready = bool(self.queue)
        if self.queue:
            logger.info(
                "live queue: loaded %d-event batch in %.2fs — %s",
                len(self.queue),
                self.build_time_s,
                self.queue_actual_counts,
            )
        return bool(self.queue)

    async def _emit_loop(self) -> None:
        """Main loop: emits events at configured TPS using rolling DB batches."""
        logger.info("live queue: emit loop started (tps=%.1f)", self.tps)
        while self.running:
            if not self._subscribers:
                self.queue = []
                self.position = 0
                self.ready = False
                self.queue_actual_counts = {}
                await asyncio.sleep(0.5)
                continue

            if self.position >= len(self.queue) and not await self._load_next_batch():
                await asyncio.sleep(1.0)
                continue

            if not self._subscribers or self.position >= len(self.queue):
                continue

            evt = self.queue[self.position]
            self.position += 1
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
        """Start the rolling emit loop as a background task."""
        async with self._lock:
            if self.running:
                logger.warning("live queue: already running")
                return
            self.running = True
            self.ready = False
            self.queue = []
            self.position = 0
            self.total_emitted = 0
            self.build_time_s = 0.0
            self.queue_actual_counts = {}
            self._band_after_case_id = {label: 0 for label in BATCH_TARGETS}
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
            self.queue = []
            self.position = 0
            self.queue_actual_counts = {}
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
