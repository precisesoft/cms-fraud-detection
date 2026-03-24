"""V2 real-time single-claim simulation endpoint with weak-supervision output."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.ai.narrative import generate_narrative
from src.api.deps import get_db
from src.api.schemas import (
    ClaimSimulationRequest,
    ClaimSimulationV2Result,
    PeerComparisonStats,
    Recommendation,
    RiskBand,
    Signal,
    risk_band_from_score,
)
from src.models.anomaly_scorer import score_provider
from src.models.weak_supervised import score_observation
from src.scoring.extract import FiredSignal
from src.scoring.score import score_case
from src.scoring.taxonomy import MIN_PEER_COUNT

router = APIRouter(prefix="/v2/claims", tags=["simulation-v2"])

_PROVIDER_SQL = """
SELECT pf.enrolled_2025       AS present_in_2025_enrollment_file,
       pf.revoked_2026        AS present_in_2026_revocation_file,
       pf.medicare_participating AS medicare_participating_ind,
       pf.provider_type,
       pf.provider_total_benes,
       pf.provider_name,
       pf.state
FROM provider_features pf
WHERE pf.npi = %s
"""

_PEER_SQL = """
SELECT count(*)                                AS peer_count,
       avg(tot_srvcs)                          AS avg_srvcs,
       stddev_pop(tot_srvcs)                   AS std_srvcs,
       avg(services_per_bene)                  AS avg_spb,
       stddev_pop(services_per_bene)           AS std_spb,
       avg(submitted_to_allowed_ratio)         AS avg_ratio,
       stddev_pop(submitted_to_allowed_ratio)  AS std_ratio,
       avg(avg_medicare_payment_amt)           AS avg_payment,
       stddev_pop(avg_medicare_payment_amt)    AS std_payment,
       avg(avg_submitted_charge)               AS avg_charge,
       stddev_pop(avg_submitted_charge)        AS std_charge
FROM provider_service_cases
WHERE provider_type = %s
  AND hcpcs_cd = %s
  AND npi != %s
"""

_FEATURES_SQL = """
SELECT * FROM provider_features WHERE npi = %s
"""

_RISK_TO_RECOMMENDATION: dict[RiskBand | None, Recommendation] = {
    RiskBand.stable: Recommendation.approve,
    RiskBand.review: Recommendation.review,
    RiskBand.high_risk: Recommendation.deny,
    None: Recommendation.review,
}


def _z_score(value: float | None, mean: float | None, std: float | None) -> float | None:
    if value is None or mean is None or std is None or std == 0:
        return None
    return (value - mean) / std


def _fired_to_signal(fs: FiredSignal) -> Signal:
    return Signal(
        name=fs.signal.name,
        category=fs.signal.category,
        direction=fs.signal.direction.value,
        value=fs.value,
        threshold=fs.signal.threshold,
        description=fs.reason or fs.signal.description,
    )


def _build_comparison(
    metric: str,
    provider_value: float,
    peer_mean: float | None,
    peer_std: float | None,
    peer_count: int,
) -> PeerComparisonStats | None:
    if peer_mean is None:
        return None
    z = _z_score(provider_value, peer_mean, peer_std)
    return PeerComparisonStats(
        metric=metric,
        provider_value=round(provider_value, 2),
        peer_mean=round(peer_mean, 2),
        z_score=round(z, 2) if z is not None else 0.0,
        percentile=None,
        peer_count=peer_count,
    )


@router.post("/simulate", response_model=ClaimSimulationV2Result)
async def simulate_claim_v2(
    req: ClaimSimulationRequest,
    conn: AsyncConnection = Depends(get_db),
) -> ClaimSimulationV2Result:
    """Score a hypothetical claim and attach weak-supervision output."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_PROVIDER_SQL, [req.npi])
        provider = await cur.fetchone()

    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {req.npi} not found")

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_PEER_SQL, [provider["provider_type"], req.hcpcs_cd, req.npi])
        peers = await cur.fetchone()

    services_per_bene = req.num_services / req.num_benes

    case: dict = {
        "present_in_2025_enrollment_file": provider["present_in_2025_enrollment_file"],
        "present_in_2026_revocation_file": provider["present_in_2026_revocation_file"],
        "medicare_participating_ind": provider["medicare_participating_ind"],
        "provider_total_benes": provider["provider_total_benes"],
    }

    peer_comparisons: list[PeerComparisonStats] = []
    peer_count = int(peers["peer_count"] or 0) if peers else 0

    if peers and peer_count >= MIN_PEER_COUNT:
        case["peer_case_count"] = peer_count
        case["peer_avg_tot_srvcs"] = peers["avg_srvcs"]

        case["service_volume_peer_z"] = _z_score(
            float(req.num_services), peers["avg_srvcs"], peers["std_srvcs"]
        )
        case["services_per_bene_peer_z"] = _z_score(
            services_per_bene, peers["avg_spb"], peers["std_spb"]
        )
        case["submitted_to_allowed_peer_z"] = _z_score(
            req.submitted_charge, peers["avg_ratio"], peers["std_ratio"]
        )
        case["payment_peer_z"] = _z_score(
            req.submitted_charge, peers["avg_payment"], peers["std_payment"]
        )

        for metric, provider_value, peer_mean, peer_std in [
            ("submitted_charge", req.submitted_charge, peers["avg_charge"], peers["std_charge"]),
            ("service_volume", float(req.num_services), peers["avg_srvcs"], peers["std_srvcs"]),
            ("services_per_bene", services_per_bene, peers["avg_spb"], peers["std_spb"]),
        ]:
            comparison = _build_comparison(
                metric,
                provider_value,
                peer_mean,
                peer_std,
                peer_count,
            )
            if comparison is not None:
                peer_comparisons.append(comparison)

    card = score_case(case)
    risk_band = risk_band_from_score(card.risk_score)
    recommendation = _RISK_TO_RECOMMENDATION.get(risk_band, Recommendation.review)
    signals = [_fired_to_signal(fs) for fs in card.signals]

    anomaly_score: float | None = None
    ml_predicted_probability: float | None = None
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_FEATURES_SQL, [req.npi])
        features_row = await cur.fetchone()
    if features_row:
        anomaly_score = score_provider(features_row)

    observation_row = {
        **provider,
        **(features_row or {}),
        "npi": req.npi,
        "hcpcs_cd": req.hcpcs_cd,
        "avg_submitted_charge": req.submitted_charge,
        "submitted_to_allowed_ratio": req.submitted_charge,
        "services_per_bene": services_per_bene,
        "peer_avg_spb": peers.get("avg_spb") if peers else None,
        "submitted_to_allowed_peer_z": case.get("submitted_to_allowed_peer_z"),
        "services_per_bene_peer_z": case.get("services_per_bene_peer_z"),
        "risk_score": card.risk_score,
        "seed_risk_score": card.risk_score,
        "total_services": float(req.num_services),
        "total_beneficiaries": float(req.num_benes),
        "graph_shared_specialty_count": 0.0,
        "is_excluded": 0.0,
    }
    ml_predicted_probability = score_observation(observation_row)

    narrative = await generate_narrative(
        npi=req.npi,
        risk_score=card.risk_score,
        risk_band=str(risk_band) if risk_band else "unknown",
        signals=[signal.model_dump() for signal in signals],
        provider_name=provider.get("provider_name"),
        provider_type=provider.get("provider_type"),
        state=provider.get("state"),
        recommendation=recommendation,
        peer_comparisons=[comparison.model_dump() for comparison in peer_comparisons],
        anomaly_score=anomaly_score,
    )

    return ClaimSimulationV2Result(
        npi=req.npi,
        hcpcs_cd=req.hcpcs_cd,
        risk_score=card.risk_score,
        risk_band=risk_band,  # type: ignore[arg-type]
        recommendation=recommendation,
        signals=signals,
        peer_comparisons=peer_comparisons,
        provider_name=provider.get("provider_name"),
        provider_type=provider.get("provider_type"),
        state=provider.get("state"),
        narrative=narrative,
        anomaly_score=anomaly_score,
        ml_predicted_probability=ml_predicted_probability,
    )
