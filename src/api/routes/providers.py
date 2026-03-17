"""Provider list and detail endpoints."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import (
    PaginationMeta,
    ProviderDetail,
    ProviderListResponse,
    ProviderSummary,
    RiskBand,
    risk_band_from_score,
)

router = APIRouter(prefix="/providers", tags=["providers"])

# Columns selected for the list view (matches ProviderSummary fields minus risk_band)
_SUMMARY_COLS = (
    "npi, provider_name, provider_type, state, city, entity_code, "
    "max_seed_risk_score, service_line_count, total_estimated_payment, revoked_2026"
)


@router.get("", response_model=ProviderListResponse)
async def list_providers(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    state: str | None = None,
    provider_type: str | None = None,
    risk_band: RiskBand | None = None,
    q: str | None = None,
    conn: AsyncConnection = Depends(get_db),
) -> ProviderListResponse:
    conditions: list[str] = []
    params: list[object] = []

    if state:
        conditions.append("state = %s")
        params.append(state)
    if provider_type:
        conditions.append("provider_type = %s")
        params.append(provider_type)
    if risk_band:
        if risk_band == RiskBand.high_risk:
            conditions.append("max_seed_risk_score >= 51")
        elif risk_band == RiskBand.review:
            conditions.append("max_seed_risk_score BETWEEN 31 AND 50")
        else:
            conditions.append("max_seed_risk_score <= 30")
    if q:
        conditions.append("(provider_name ILIKE %s OR npi ILIKE %s)")
        pattern = f"%{q}%"
        params.extend([pattern, pattern])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(f"SELECT count(*) AS cnt FROM provider_features {where}", params)
        row = await cur.fetchone()
        total = row["cnt"] if row else 0

        offset = (page - 1) * per_page
        await cur.execute(
            f"SELECT {_SUMMARY_COLS} FROM provider_features {where} "
            "ORDER BY max_seed_risk_score DESC NULLS LAST "
            "LIMIT %s OFFSET %s",
            [*params, per_page, offset],
        )
        rows = await cur.fetchall()

    data = [
        ProviderSummary(**r, risk_band=risk_band_from_score(r["max_seed_risk_score"])) for r in rows
    ]
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )
    return ProviderListResponse(data=data, meta=meta)


@router.get("/{npi}", response_model=ProviderDetail)
async def get_provider(
    npi: str,
    conn: AsyncConnection = Depends(get_db),
) -> ProviderDetail:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT * FROM provider_features WHERE npi = %s", [npi])
        row = await cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Provider {npi} not found")

    return ProviderDetail(**row, risk_band=risk_band_from_score(row["max_seed_risk_score"]))
