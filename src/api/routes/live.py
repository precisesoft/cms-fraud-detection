"""Real-time payment simulation stream via Server-Sent Events (SSE).

Samples random claims from the database, scores each one live through
the scoring engine, and streams results to the frontend for the
Live Payment Monitor demo.

NOTE: No auth on SSE stream — demo-scoped. Production: gate via Istio JWT policy.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.models.anomaly_scorer import score_provider
from src.scoring.score import score_case
from src.scoring.taxonomy import SignalDirection

router = APIRouter(prefix="/live", tags=["live"])

# ---------------------------------------------------------------------------
# SQL — fetch a random claim row with all columns needed for scoring
# ---------------------------------------------------------------------------

_RANDOM_CLAIM_SQL = """
SELECT case_id, npi, provider_name, state, city,
       hcpcs_cd, hcpcs_desc, place_of_service, provider_type,
       avg_submitted_charge, tot_srvcs, tot_benes,
       present_in_2025_enrollment_file, present_in_2026_revocation_file,
       medicare_participating_ind, provider_total_benes,
       peer_scope, peer_case_count, peer_avg_tot_srvcs,
       service_volume_peer_z, services_per_bene_peer_z,
       submitted_to_allowed_peer_z, payment_peer_z,
       top_code_share, service_hhi
FROM provider_service_cases
ORDER BY RANDOM()
LIMIT 1
"""

_FEATURES_SQL = """SELECT * FROM provider_features WHERE npi = %s"""


# ---------------------------------------------------------------------------
# SSE stream endpoint
# ---------------------------------------------------------------------------


@router.get("/stream")
async def stream_claims(
    conn: AsyncConnection = Depends(get_db),
    interval: float = Query(default=1.5, ge=0.5, le=5.0),
    limit: int = Query(default=0, ge=0),
):
    """Stream scored claims as Server-Sent Events.

    Each event contains a randomly sampled claim scored in real-time
    through the 14-signal scoring engine with live latency measurement.
    """

    async def event_generator():
        count = 0
        while limit == 0 or count < limit:
            try:
                # 1. Sample a random claim
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(_RANDOM_CLAIM_SQL)
                    row = await cur.fetchone()

                if not row:
                    await asyncio.sleep(interval)
                    continue

                # 2. Score it live and measure latency
                start = time.monotonic()
                card = score_case(dict(row))
                latency_ms = (time.monotonic() - start) * 1000

                # 3. Get anomaly score (optional, non-fatal)
                anomaly_score: float | None = None
                try:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(_FEATURES_SQL, [row["npi"]])
                        features_row = await cur.fetchone()
                    if features_row:
                        anomaly_score = score_provider(features_row)
                except Exception:
                    pass

                # 4. Build event payload
                risk_signals = [
                    s.signal.name
                    for s in card.signals
                    if s.signal.direction == SignalDirection.risk
                ]

                event = {
                    "event_id": f"evt_{count:05d}",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "npi": row["npi"],
                    "provider_name": row.get("provider_name") or "Unknown",
                    "state": row.get("state") or "Unknown",
                    "city": row.get("city") or "",
                    "hcpcs_code": row.get("hcpcs_cd") or "",
                    "hcpcs_desc": row.get("hcpcs_desc") or "",
                    "submitted_charge": float(row.get("avg_submitted_charge") or 0),
                    "risk_score": card.risk_score,
                    "legitimacy_score": card.legitimacy_score,
                    "case_label": card.case_label.value,
                    "anomaly_score": anomaly_score,
                    "signals": risk_signals,
                    "scoring_latency_ms": round(latency_ms, 1),
                }

                yield f"data: {json.dumps(event)}\n\n"
                count += 1

            except Exception:
                # Connection lost or DB error — stop gracefully
                break

            await asyncio.sleep(interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
