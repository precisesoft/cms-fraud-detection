"""V2 on-the-fly scoring endpoint with hybrid weak-supervised outputs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.ai.narrative import generate_narrative
from src.api.deps import get_db
from src.api.routes.score import (
    _FEATURES_SQL,
    _PEER_SQL,
    _PROVIDER_SQL,
    _fired_to_signal,
    _z_score,
)
from src.api.schemas import ScoreRequest, ScoreV2Result, risk_band_from_score
from src.models.anomaly_scorer import score_provider
from src.models.weak_supervised import compute_composite_score, score_observation
from src.scoring.score import score_case
from src.scoring.taxonomy import MIN_PEER_COUNT

router = APIRouter(prefix="/v2/score", tags=["scoring-v2"])


def _build_observation_row(
    req: ScoreRequest,
    provider: dict,
    features_row: dict | None,
    case: dict,
    peers: dict | None,
    legacy_risk_score: int,
) -> dict:
    provider_total_benes = provider.get("provider_total_benes")
    services_per_bene = None
    if req.tot_srvcs is not None and provider_total_benes is not None and provider_total_benes != 0:
        services_per_bene = float(req.tot_srvcs) / float(provider_total_benes)

    return {
        **provider,
        **(features_row or {}),
        "npi": req.npi,
        "hcpcs_cd": req.hcpcs_cd,
        "avg_submitted_charge": req.avg_submitted_charge,
        "submitted_to_allowed_ratio": req.avg_submitted_charge,
        "services_per_bene": services_per_bene,
        "peer_avg_spb": peers.get("avg_spb") if peers else None,
        "submitted_to_allowed_peer_z": case.get("submitted_to_allowed_peer_z"),
        "services_per_bene_peer_z": case.get("services_per_bene_peer_z"),
        "risk_score": legacy_risk_score,
        "seed_risk_score": legacy_risk_score,
        "total_services": req.tot_srvcs,
        "total_beneficiaries": provider_total_benes,
        "graph_shared_specialty_count": 0.0,
        "is_excluded": 0.0,
    }


@router.post("", response_model=ScoreV2Result)
async def score_claim_v2(
    req: ScoreRequest,
    conn: AsyncConnection = Depends(get_db),
) -> ScoreV2Result:
    """Score a claim on the fly and attach hybrid weak-supervised outputs."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_PROVIDER_SQL, [req.npi])
        provider = await cur.fetchone()

    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {req.npi} not found")

    case: dict = {
        "present_in_2025_enrollment_file": provider["present_in_2025_enrollment_file"],
        "present_in_2026_revocation_file": provider["present_in_2026_revocation_file"],
        "medicare_participating_ind": provider["medicare_participating_ind"],
        "provider_total_benes": provider["provider_total_benes"],
    }

    peers: dict | None = None
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
            case["services_per_bene_peer_z"] = None
            case["submitted_to_allowed_peer_z"] = _z_score(
                req.avg_submitted_charge, peers["avg_ratio"], peers["std_ratio"]
            )
            case["payment_peer_z"] = _z_score(
                req.avg_submitted_charge, peers["avg_payment"], peers["std_payment"]
            )

    card = score_case(case)
    risk_band = risk_band_from_score(card.risk_score)
    signals = [_fired_to_signal(fs) for fs in card.signals]

    anomaly_score: float | None = None
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_FEATURES_SQL, [req.npi])
        features_row = await cur.fetchone()
    if features_row:
        anomaly_score = score_provider(features_row)

    observation_row = _build_observation_row(
        req=req,
        provider=provider,
        features_row=features_row,
        case=case,
        peers=peers,
        legacy_risk_score=card.risk_score,
    )
    ml_predicted_probability = score_observation(observation_row)
    composite_score, composite_risk_label = compute_composite_score(
        observation_row,
        ml_predicted_probability,
    )

    narrative = await generate_narrative(
        npi=req.npi,
        risk_score=card.risk_score,
        risk_band=str(risk_band) if risk_band else "unknown",
        signals=[s.model_dump() for s in signals],
        provider_type=provider.get("provider_type"),
        anomaly_score=anomaly_score,
    )

    return ScoreV2Result(
        npi=req.npi,
        risk_score=card.risk_score,
        legitimacy_score=card.legitimacy_score,
        risk_band=risk_band,  # type: ignore[arg-type]
        signals=signals,
        narrative=narrative,
        anomaly_score=anomaly_score,
        ml_predicted_probability=ml_predicted_probability,
        composite_score=composite_score,
        composite_risk_label=composite_risk_label,
    )
