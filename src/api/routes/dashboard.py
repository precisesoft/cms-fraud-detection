"""Dashboard endpoints — aggregate stats and geographic heatmap.

Performance: Both endpoints use a TTL cache (60 s) so repeated loads
within the same minute hit memory instead of the database.  Queries
run sequentially on the single connection (psycopg async connections
cannot multiplex concurrent cursors).
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Response
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
from src.scoring.taxonomy import HIGH_RISK_SCORE_THRESHOLD, STABLE_RISK_CEILING

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ---------------------------------------------------------------------------
# In-memory TTL cache (simple, process-local)
# ---------------------------------------------------------------------------

_CACHE_TTL = 60  # seconds

_dashboard_cache: DashboardStats | None = None
_dashboard_cache_ts: float = 0.0

_heatmap_cache: HeatmapResponse | None = None
_heatmap_cache_ts: float = 0.0


def invalidate_dashboard_cache() -> None:
    """Call after a pipeline run or data ingest to force a refresh."""
    global _dashboard_cache, _dashboard_cache_ts, _heatmap_cache, _heatmap_cache_ts
    _dashboard_cache = None
    _dashboard_cache_ts = 0.0
    _heatmap_cache = None
    _heatmap_cache_ts = 0.0


# ---------------------------------------------------------------------------
# GET /dashboard — aggregate stats
# ---------------------------------------------------------------------------

_COUNTS_SQL = """
SELECT count(*)::int AS total_providers,
       (SELECT count(*)::int FROM provider_service_cases) AS total_cases
FROM provider_features
"""

_REVIEW_LO = STABLE_RISK_CEILING + 1
_REVIEW_HI = HIGH_RISK_SCORE_THRESHOLD - 1

_DISTRIBUTION_SQL = f"""
SELECT
  count(*) FILTER (WHERE max_seed_risk_score >= {HIGH_RISK_SCORE_THRESHOLD})::int
    AS high_risk,
  count(*) FILTER (WHERE max_seed_risk_score BETWEEN {_REVIEW_LO} AND {_REVIEW_HI})::int
    AS review,
  count(*) FILTER (
    WHERE max_seed_risk_score <= {STABLE_RISK_CEILING}
       OR max_seed_risk_score IS NULL
  )::int AS stable
FROM provider_features
"""

_TOP_SQL = """
SELECT npi, provider_name, provider_type, state, city, entity_code,
       max_seed_risk_score, service_line_count, total_estimated_payment, revoked_2026
FROM provider_features
ORDER BY max_seed_risk_score DESC NULLS LAST
LIMIT 10
"""


async def _fetch_counts(conn: AsyncConnection) -> dict:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_COUNTS_SQL)
        return await cur.fetchone() or {}


async def _fetch_distribution(conn: AsyncConnection) -> dict:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_DISTRIBUTION_SQL)
        return await cur.fetchone() or {}


async def _fetch_top(conn: AsyncConnection) -> list[dict]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_TOP_SQL)
        return await cur.fetchall()


@router.get("", response_model=DashboardStats)
async def get_dashboard(
    response: Response,
    conn: AsyncConnection = Depends(get_db),
) -> DashboardStats:
    """Return aggregate stats, risk distribution, and top flagged providers."""
    global _dashboard_cache, _dashboard_cache_ts

    now = time.monotonic()
    if _dashboard_cache is not None and (now - _dashboard_cache_ts) < _CACHE_TTL:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = f"public, max-age={_CACHE_TTL}"
        return _dashboard_cache

    # Run queries sequentially — psycopg async connections cannot
    # multiplex concurrent cursors on a single connection.
    counts = await _fetch_counts(conn)
    dist = await _fetch_distribution(conn)
    top_rows = await _fetch_top(conn)

    total_providers = counts.get("total_providers", 0)
    total_cases = counts.get("total_cases", 0)

    distribution = RiskDistribution(
        high_risk=dist.get("high_risk", 0),
        review=dist.get("review", 0),
        stable=dist.get("stable", 0),
    )

    top_providers = [
        ProviderSummary(
            **r,
            risk_band=risk_band_from_score(r.get("max_seed_risk_score")),
        )
        for r in top_rows
    ]

    result = DashboardStats(
        total_providers=total_providers,
        total_cases=total_cases,
        risk_distribution=distribution,
        top_providers=top_providers,
    )

    _dashboard_cache = result
    _dashboard_cache_ts = now
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = f"public, max-age={_CACHE_TTL}"
    return result


# ---------------------------------------------------------------------------
# GET /dashboard/heatmap — state-level risk map
# ---------------------------------------------------------------------------

_HEATMAP_SQL = f"""
SELECT state,
       count(*)::int AS provider_count,
       round(avg(max_seed_risk_score)::numeric, 1)::float
           AS avg_risk_score,
       count(*) FILTER (
           WHERE max_seed_risk_score >= {HIGH_RISK_SCORE_THRESHOLD}
       )::int AS flagged_count
FROM provider_features
WHERE state IS NOT NULL
GROUP BY state
ORDER BY avg_risk_score DESC
"""


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    response: Response,
    conn: AsyncConnection = Depends(get_db),
) -> HeatmapResponse:
    """Return state-level aggregated risk data for the geographic heatmap."""
    global _heatmap_cache, _heatmap_cache_ts

    now = time.monotonic()
    if _heatmap_cache is not None and (now - _heatmap_cache_ts) < _CACHE_TTL:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = f"public, max-age={_CACHE_TTL}"
        return _heatmap_cache

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_HEATMAP_SQL)
        rows = await cur.fetchall()

    result = HeatmapResponse(data=[HeatmapEntry(**r) for r in rows])

    _heatmap_cache = result
    _heatmap_cache_ts = now
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = f"public, max-age={_CACHE_TTL}"
    return result
