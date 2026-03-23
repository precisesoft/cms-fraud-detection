"""Claims list endpoint — paginated provider-service cases with filtering."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import Claim, ClaimListResponse, PaginationMeta

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
