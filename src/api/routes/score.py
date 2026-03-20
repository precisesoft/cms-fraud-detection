"""On-the-fly scoring endpoint — score a claim not yet in the database."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.ai.narrative import generate_narrative
from src.api.deps import get_db
from src.api.schemas import ScoreRequest, ScoreResult, Signal, risk_band_from_score
from src.models.anomaly_scorer import score_provider
from src.scoring.extract import FiredSignal
from src.scoring.score import score_case
from src.scoring.taxonomy import MIN_PEER_COUNT

router = APIRouter(prefix="/score", tags=["scoring"])

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_PROVIDER_SQL = """
SELECT enrolled_2025 AS present_in_2025_enrollment_file,
       revoked_2026  AS present_in_2026_revocation_file,
       medicare_participating AS medicare_participating_ind,
       provider_type,
       provider_total_benes
FROM provider_features
WHERE npi = %s
"""

_FEATURES_SQL = """
SELECT * FROM provider_features WHERE npi = %s
"""

_PEER_SQL = """
SELECT count(*)                          AS peer_count,
       avg(tot_srvcs)                    AS avg_srvcs,
       stddev_pop(tot_srvcs)             AS std_srvcs,
       avg(services_per_bene)            AS avg_spb,
       stddev_pop(services_per_bene)     AS std_spb,
       avg(submitted_to_allowed_ratio)   AS avg_ratio,
       stddev_pop(submitted_to_allowed_ratio) AS std_ratio,
       avg(avg_medicare_payment_amt)     AS avg_payment,
       stddev_pop(avg_medicare_payment_amt)   AS std_payment
FROM provider_service_cases
WHERE provider_type = %s
  AND hcpcs_cd = %s
  AND npi != %s
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _z_score(value: float | None, mean: float | None, std: float | None) -> float | None:
    """Compute z-score, returning None if inputs are missing or std is zero."""
    if value is None or mean is None or std is None or std == 0:
        return None
    return (value - mean) / std


def _fired_to_signal(fs: FiredSignal) -> Signal:
    """Map an internal FiredSignal to the API Signal schema."""
    return Signal(
        name=fs.signal.name,
        category=fs.signal.category,
        direction=fs.signal.direction.value,
        value=fs.value,
        threshold=fs.signal.threshold,
        description=fs.reason or fs.signal.description,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("", response_model=ScoreResult)
async def score_claim(
    req: ScoreRequest,
    conn: AsyncConnection = Depends(get_db),
) -> ScoreResult:
    """Score a claim on the fly.

    Looks up the provider profile and peer baselines from the database,
    computes z-scores from the submitted values, and runs the scoring engine.
    """
    # 1. Look up provider profile
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_PROVIDER_SQL, [req.npi])
        provider = await cur.fetchone()

    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {req.npi} not found")

    # 2. Build base case dict from provider profile
    case: dict = {
        "present_in_2025_enrollment_file": provider["present_in_2025_enrollment_file"],
        "present_in_2026_revocation_file": provider["present_in_2026_revocation_file"],
        "medicare_participating_ind": provider["medicare_participating_ind"],
        "provider_total_benes": provider["provider_total_benes"],
    }

    # 3. Fetch peer baselines and compute z-scores (if HCPCS provided)
    if req.hcpcs_cd:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(_PEER_SQL, [provider["provider_type"], req.hcpcs_cd, req.npi])
            peers = await cur.fetchone()

        if peers and (peers["peer_count"] or 0) >= MIN_PEER_COUNT:
            case["peer_case_count"] = peers["peer_count"]
            case["peer_avg_tot_srvcs"] = peers["avg_srvcs"]

            case["service_volume_peer_z"] = _z_score(
                req.tot_srvcs, peers["avg_srvcs"], peers["std_srvcs"]
            )
            # ScoreRequest has no num_benes — cannot compute per-bene intensity
            case["services_per_bene_peer_z"] = None
            # ScoreRequest has no avg_medicare_allowed_amt — use submitted charge as proxy
            case["submitted_to_allowed_peer_z"] = _z_score(
                req.avg_submitted_charge, peers["avg_ratio"], peers["std_ratio"]
            )
            # ScoreRequest has no avg_medicare_payment_amt — use submitted charge as proxy
            case["payment_peer_z"] = _z_score(
                req.avg_submitted_charge, peers["avg_payment"], peers["std_payment"]
            )

    # 4. Score
    card = score_case(case)

    # 5. Map to API response
    risk_band = risk_band_from_score(card.risk_score)
    signals = [_fired_to_signal(fs) for fs in card.signals]

    # 6. Anomaly score from isolation forest
    anomaly_score: float | None = None
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_FEATURES_SQL, [req.npi])
        features_row = await cur.fetchone()
    if features_row:
        anomaly_score = score_provider(features_row)

    # 7. Generate AI narrative (non-blocking, non-fatal)
    narrative = await generate_narrative(
        npi=req.npi,
        risk_score=card.risk_score,
        risk_band=str(risk_band) if risk_band else "unknown",
        signals=[s.model_dump() for s in signals],
        provider_type=provider.get("provider_type"),
        anomaly_score=anomaly_score,
    )

    return ScoreResult(
        npi=req.npi,
        risk_score=card.risk_score,
        legitimacy_score=card.legitimacy_score,
        risk_band=risk_band,  # type: ignore[arg-type]
        signals=signals,
        narrative=narrative,
        anomaly_score=anomaly_score,
    )
