"""Fraud ring cluster endpoint — detect connected provider networks.

Uses a recursive CTE to traverse provider_features via shared zip code
or organization name, returning the cluster of flagged providers around
a seed NPI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import ClusterMember, FraudClusterResponse, RiskBand, risk_band_from_score

router = APIRouter(prefix="/cluster", tags=["cluster"])

# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------

_SEED_EXISTS_SQL = """
SELECT 1 FROM provider_features WHERE npi = %(npi)s
"""

_CLUSTER_SQL = """
WITH RECURSIVE ring AS (
    SELECT npi, zip5, provider_name, entity_code,
           0 AS hops, 'SEED' AS link_type
    FROM provider_features
    WHERE npi = %(npi)s

    UNION

    SELECT pf.npi, pf.zip5, pf.provider_name, pf.entity_code,
           r.hops + 1,
           CASE
               WHEN pf.zip5 = r.zip5 THEN 'SAME_ZIP'
               ELSE 'SAME_ORG'
           END
    FROM provider_features pf
    JOIN ring r ON (
        (pf.zip5 = r.zip5 AND pf.zip5 IS NOT NULL)
        OR (pf.provider_name = r.provider_name
            AND pf.entity_code = 'O' AND r.entity_code = 'O')
    )
    WHERE r.hops < 3
      AND pf.npi != r.npi
)
SELECT DISTINCT ON (r.npi)
       r.npi,
       pf.provider_name,
       pf.provider_type,
       pf.state,
       pf.zip5,
       pf.max_seed_risk_score AS risk_score,
       pf.revoked_2026 AS revoked,
       r.link_type,
       r.hops
FROM ring r
JOIN provider_features pf ON pf.npi = r.npi
WHERE pf.max_seed_risk_score >= %(threshold)s
  AND r.link_type != 'SEED'
ORDER BY r.npi, r.hops
LIMIT 26
"""


def _risk_band(score: int | None) -> RiskBand | None:
    return risk_band_from_score(score)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/{npi}", response_model=FraudClusterResponse)
async def get_fraud_cluster(
    npi: str,
    threshold: int = Query(
        default=31,
        ge=0,
        le=100,
        description="Min risk score for cluster members",
    ),
    conn: AsyncConnection = Depends(get_db),
) -> FraudClusterResponse:
    """Return fraud ring cluster: providers connected via shared zip or org."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_SEED_EXISTS_SQL, {"npi": npi})
        if not await cur.fetchone():
            raise HTTPException(status_code=404, detail="Provider not found")

        await cur.execute(_CLUSTER_SQL, {"npi": npi, "threshold": threshold})
        rows = await cur.fetchall()

    truncated = len(rows) > 25
    members_rows = rows[:25]

    members = [
        ClusterMember(
            npi=r["npi"],
            provider_name=r.get("provider_name"),
            provider_type=r.get("provider_type"),
            state=r.get("state"),
            zip5=r.get("zip5"),
            risk_score=r.get("risk_score"),
            risk_band=_risk_band(r.get("risk_score")),
            revoked=bool(r.get("revoked")),
            link_type=r["link_type"],
            hops=r["hops"],
        )
        for r in members_rows
    ]

    all_npis = sorted({npi} | {m.npi for m in members})
    high_risk = sum(1 for m in members if m.risk_band == RiskBand.high_risk)
    revoked = sum(1 for m in members if m.revoked)

    return FraudClusterResponse(
        npi=npi,
        cluster_id="_".join(all_npis),
        members=members,
        cluster_size=len(all_npis),
        high_risk_count=high_risk,
        revoked_count=revoked,
        truncated=truncated,
    )
