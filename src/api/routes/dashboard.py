"""Dashboard endpoints — aggregate stats and geographic heatmap."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import (
    DashboardStats,
    HeatmapEntry,
    HeatmapResponse,
    ProviderSummary,
    RiskDistribution,
    risk_band_from_score,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ---------------------------------------------------------------------------
# GET /dashboard — aggregate stats
# ---------------------------------------------------------------------------

_COUNTS_SQL = """
SELECT count(*)::int AS total_providers,
       (SELECT count(*)::int FROM provider_service_cases) AS total_cases
FROM provider_features
"""

_DISTRIBUTION_SQL = """
SELECT
  count(*) FILTER (WHERE max_seed_risk_score >= 51)::int AS high_risk,
  count(*) FILTER (WHERE max_seed_risk_score BETWEEN 31 AND 50)::int AS review,
  count(*) FILTER (WHERE max_seed_risk_score <= 30 OR max_seed_risk_score IS NULL)::int AS stable
FROM provider_features
"""

_TOP_SQL = """
SELECT npi, provider_name, provider_type, state, city, entity_code,
       max_seed_risk_score, service_line_count, total_estimated_payment, revoked_2026
FROM provider_features
ORDER BY max_seed_risk_score DESC NULLS LAST
LIMIT 10
"""


@router.get("", response_model=DashboardStats)
async def get_dashboard(
    conn: AsyncConnection = Depends(get_db),
) -> DashboardStats:
    """Return aggregate stats, risk distribution, and top flagged providers."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_COUNTS_SQL)
        counts = await cur.fetchone()

        await cur.execute(_DISTRIBUTION_SQL)
        dist = await cur.fetchone()

        await cur.execute(_TOP_SQL)
        top_rows = await cur.fetchall()

    total_providers = counts["total_providers"] if counts else 0
    total_cases = counts["total_cases"] if counts else 0

    distribution = RiskDistribution(
        high_risk=dist["high_risk"] if dist else 0,
        review=dist["review"] if dist else 0,
        stable=dist["stable"] if dist else 0,
    )

    top_providers = [
        ProviderSummary(
            **r,
            risk_band=risk_band_from_score(r.get("max_seed_risk_score")),
        )
        for r in top_rows
    ]

    return DashboardStats(
        total_providers=total_providers,
        total_cases=total_cases,
        risk_distribution=distribution,
        top_providers=top_providers,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/heatmap — state-level risk map
# ---------------------------------------------------------------------------

_HEATMAP_SQL = """
SELECT state,
       count(*)::int AS provider_count,
       round(avg(max_seed_risk_score)::numeric, 1)::float AS avg_risk_score,
       count(*) FILTER (WHERE max_seed_risk_score >= 51)::int AS flagged_count
FROM provider_features
WHERE state IS NOT NULL
GROUP BY state
ORDER BY avg_risk_score DESC
"""


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    conn: AsyncConnection = Depends(get_db),
) -> HeatmapResponse:
    """Return state-level aggregated risk data for the geographic heatmap."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_HEATMAP_SQL)
        rows = await cur.fetchall()

    data = [HeatmapEntry(**r) for r in rows]
    return HeatmapResponse(data=data)
