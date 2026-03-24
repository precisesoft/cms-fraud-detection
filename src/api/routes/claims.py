"""Claims list endpoint — paginated provider-service cases with filtering."""

from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import (
    Claim,
    ClaimListResponse,
    ClaimScoreDetails,
    PaginationMeta,
    risk_band_from_score,
)
from src.models.weak_supervised import compute_anomaly_score

router = APIRouter(prefix="/claims", tags=["claims"])

_COLS = (
    "case_id, npi, provider_last_org_name, provider_first_name, "
    "provider_credentials, provider_entity_code, provider_city, provider_state, "
    "provider_zip5, provider_type, medicare_participating_ind, "
    "hcpcs_cd, hcpcs_desc, place_of_service, "
    "tot_benes, tot_srvcs, tot_bene_day_srvcs, "
    "avg_submitted_charge, avg_medicare_allowed_amt, avg_medicare_payment_amt, "
    "estimated_case_payment_amt, services_per_bene, "
    "submitted_to_allowed_ratio, payment_to_allowed_ratio, "
    "peer_scope, peer_case_count, peer_avg_tot_srvcs, "
    "service_volume_peer_z, services_per_bene_peer_z, "
    "submitted_to_allowed_peer_z, payment_peer_z, "
    "seed_risk_score, seed_legitimacy_score, seed_case_label, "
    "seed_risk_reasons, seed_legitimacy_reasons"
)


@router.get("", response_model=ClaimListResponse)
async def list_claims(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    npi: str | None = None,
    case_label: str | None = None,
    state: str | None = None,
    provider_type: str | None = None,
    risk_min: int | None = Query(None, ge=0, le=100),
    risk_max: int | None = Query(None, ge=0, le=100),
    conn: AsyncConnection = Depends(get_db),
) -> ClaimListResponse:
    conditions: list[str] = []
    params: list[object] = []

    if npi:
        conditions.append("npi = %s")
        params.append(npi)
    if case_label:
        conditions.append("seed_case_label = %s")
        params.append(case_label)
    if state:
        conditions.append("provider_state = %s")
        params.append(state)
    if provider_type:
        conditions.append("provider_type = %s")
        params.append(provider_type)
    if risk_min is not None:
        conditions.append("seed_risk_score >= %s")
        params.append(risk_min)
    if risk_max is not None:
        conditions.append("seed_risk_score <= %s")
        params.append(risk_max)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(f"SELECT count(*) AS cnt FROM provider_service_cases {where}", params)
        row = await cur.fetchone()
        total = row["cnt"] if row else 0

        offset = (page - 1) * per_page
        await cur.execute(
            f"SELECT {_COLS} FROM provider_service_cases {where} "
            "ORDER BY seed_risk_score DESC NULLS LAST "
            "LIMIT %s OFFSET %s",
            [*params, per_page, offset],
        )
        rows = await cur.fetchall()

    data = [Claim(**r) for r in rows]
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )
    return ClaimListResponse(data=data, meta=meta)


@router.get("/{case_id}", response_model=Claim)
async def get_claim(
    case_id: str,
    conn: AsyncConnection = Depends(get_db),
) -> Claim:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            f"SELECT {_COLS} FROM provider_service_cases WHERE case_id = %s",
            (case_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Claim not found")
    return Claim(**row)


def _hybrid_label_from_score(
    score: float | None,
) -> Literal["low", "medium", "high", "critical"] | None:
    if score is None:
        return None
    if score >= 90.0:
        return "critical"
    if score >= 70.0:
        return "high"
    if score >= 40.0:
        return "medium"
    return "low"


@router.get("/{case_id}/score-details", response_model=ClaimScoreDetails)
async def get_claim_score_details(
    case_id: str,
    conn: AsyncConnection = Depends(get_db),
) -> ClaimScoreDetails:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            f"SELECT {_COLS} FROM provider_service_cases WHERE case_id = %s",
            (case_id,),
        )
        claim_row = await cur.fetchone()

    if not claim_row:
        raise HTTPException(status_code=404, detail="Claim not found")

    anomaly_score = compute_anomaly_score(claim_row)

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT model_name, model_version
            FROM trained_models
            ORDER BY trained_at DESC NULLS LAST, id DESC
            LIMIT 1
            """
        )
        latest_model = await cur.fetchone()

    score_row: dict | None = None
    if latest_model:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT predicted_probability,
                       composite_score,
                       risk_label,
                       model_name,
                       model_version
                FROM observation_model_scores
                WHERE case_id = %s
                  AND model_name = %s
                  AND model_version = %s
                ORDER BY scored_at DESC, id DESC
                LIMIT 1
                """,
                [case_id, latest_model["model_name"], latest_model["model_version"]],
            )
            score_row = await cur.fetchone()

    hybrid_score = score_row["composite_score"] if score_row else None
    hybrid_risk_label = None
    if score_row and score_row.get("risk_label"):
        hybrid_risk_label = score_row["risk_label"]
    else:
        hybrid_risk_label = _hybrid_label_from_score(hybrid_score)

    model_name = score_row["model_name"] if score_row else None
    if model_name is None and latest_model:
        model_name = latest_model["model_name"]

    model_version = score_row["model_version"] if score_row else None
    if model_version is None and latest_model:
        model_version = latest_model["model_version"]

    return ClaimScoreDetails(
        case_id=case_id,
        npi=claim_row["npi"],
        explainable_risk_score=claim_row.get("seed_risk_score"),
        explainable_risk_band=risk_band_from_score(claim_row.get("seed_risk_score")),
        anomaly_score=round(float(anomaly_score), 1),
        ml_predicted_probability=score_row["predicted_probability"] if score_row else None,
        hybrid_composite_score=hybrid_score,
        hybrid_risk_label=hybrid_risk_label,
        model_name=model_name,
        model_version=model_version,
    )
