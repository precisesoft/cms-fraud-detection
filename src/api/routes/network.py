"""Network risk endpoint — co-located and co-organization flagged providers.

Answers the question: "Does this provider share a zip code or organization
name with other high-risk providers?" — a graph-derived fraud signal that
justifies relationship analysis.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import NetworkNeighbor, NetworkRiskResponse
from src.scoring.taxonomy import HIGH_RISK_SCORE_THRESHOLD

router = APIRouter(prefix="/network", tags=["network"])

# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------

_PROVIDER_LOCATION_SQL = """
SELECT npi, provider_name, provider_type, state, zip5, city,
       max_seed_risk_score, revoked_2026
FROM provider_features
WHERE npi = %(npi)s
"""

_SAME_ZIP_SQL = """
SELECT npi, provider_name, provider_type, state, zip5, city,
       max_seed_risk_score, revoked_2026
FROM provider_features
WHERE zip5 = %(zip5)s
  AND npi != %(npi)s
  AND max_seed_risk_score >= %(threshold)s
ORDER BY max_seed_risk_score DESC
LIMIT 20
"""

_SAME_ORG_SQL = """
SELECT npi, provider_name, provider_type, state, zip5, city,
       max_seed_risk_score, revoked_2026
FROM provider_features
WHERE provider_name = %(org_name)s
  AND npi != %(npi)s
  AND entity_code = 'O'
ORDER BY max_seed_risk_score DESC
LIMIT 10
"""

_ZIP_RISK_STATS_SQL = f"""
SELECT count(*) AS total_in_zip,
       count(*) FILTER (
           WHERE max_seed_risk_score >= {HIGH_RISK_SCORE_THRESHOLD}
       ) AS high_risk_in_zip,
       count(*) FILTER (WHERE revoked_2026 = 1) AS revoked_in_zip,
       avg(max_seed_risk_score) AS avg_risk_in_zip
FROM provider_features
WHERE zip5 = %(zip5)s
"""


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/{npi}", response_model=NetworkRiskResponse)
async def get_network_risk(
    npi: str,
    threshold: int = Query(default=31, ge=0, le=100, description="Min risk score for neighbors"),
    conn: AsyncConnection = Depends(get_db),
) -> NetworkRiskResponse:
    """Return network risk context: co-located and co-org flagged providers."""
    async with conn.cursor(row_factory=dict_row) as cur:
        # Get the target provider
        await cur.execute(_PROVIDER_LOCATION_SQL, {"npi": npi})
        provider = await cur.fetchone()

        if not provider:
            return NetworkRiskResponse(
                npi=npi,
                zip5=None,
                same_zip_flagged=[],
                same_org_flagged=[],
                zip_risk_summary=None,
            )

        zip5 = provider.get("zip5")
        org_name = provider.get("provider_name")

        # Find flagged providers in same zip
        same_zip: list[dict] = []
        if zip5:
            await cur.execute(_SAME_ZIP_SQL, {"zip5": zip5, "npi": npi, "threshold": threshold})
            same_zip = await cur.fetchall()

        # Find flagged providers with same org name (orgs only)
        same_org: list[dict] = []
        if org_name:
            await cur.execute(_SAME_ORG_SQL, {"org_name": org_name, "npi": npi})
            same_org = await cur.fetchall()

        # Zip-level risk stats
        zip_stats = None
        if zip5:
            await cur.execute(_ZIP_RISK_STATS_SQL, {"zip5": zip5})
            zip_stats = await cur.fetchone()

    return NetworkRiskResponse(
        npi=npi,
        zip5=zip5,
        same_zip_flagged=[
            NetworkNeighbor(
                npi=r["npi"],
                provider_name=r.get("provider_name"),
                provider_type=r.get("provider_type"),
                state=r.get("state"),
                risk_score=r.get("max_seed_risk_score"),
                revoked=bool(r.get("revoked_2026")),
            )
            for r in same_zip
        ],
        same_org_flagged=[
            NetworkNeighbor(
                npi=r["npi"],
                provider_name=r.get("provider_name"),
                provider_type=r.get("provider_type"),
                state=r.get("state"),
                risk_score=r.get("max_seed_risk_score"),
                revoked=bool(r.get("revoked_2026")),
            )
            for r in same_org
        ],
        zip_risk_summary={
            "total_in_zip": zip_stats["total_in_zip"],
            "high_risk_in_zip": zip_stats["high_risk_in_zip"],
            "revoked_in_zip": zip_stats["revoked_in_zip"],
            "avg_risk_in_zip": round(float(zip_stats["avg_risk_in_zip"] or 0), 1),
        }
        if zip_stats
        else None,
    )
