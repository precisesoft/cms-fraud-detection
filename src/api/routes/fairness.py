"""Fairness analysis endpoint — flagging rates by geography and specialty."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import CohortFairness, FairnessReport, RevocationImpact
from src.scoring.taxonomy import REVOKED_PROVIDER

router = APIRouter(prefix="/fairness", tags=["fairness"])

# Providers at or above this risk score are "flagged"
DEFAULT_THRESHOLD = 51

# Derived from scoring taxonomy — single source of truth.
# The blind approximation only adjusts risk (not legitimacy) because the
# flagging threshold is based on risk_score alone. Legitimacy changes from
# removing the no_revocation signal don't affect the >= threshold comparison.
assert REVOKED_PROVIDER.points is not None, "revoked_provider signal must have points"
REVOCATION_RISK_POINTS: int = REVOKED_PROVIDER.points

_STATE_SQL = """
SELECT state AS cohort,
       count(*)::int AS provider_count,
       count(*) FILTER (WHERE max_seed_risk_score >= %s)::int AS flagged_count
FROM provider_features
WHERE state IS NOT NULL
GROUP BY state
ORDER BY state
"""

_SPECIALTY_SQL = """
SELECT provider_type AS cohort,
       count(*)::int AS provider_count,
       count(*) FILTER (WHERE max_seed_risk_score >= %s)::int AS flagged_count
FROM provider_features
WHERE provider_type IS NOT NULL
GROUP BY provider_type
ORDER BY provider_type
"""

_OVERALL_SQL = """
SELECT count(*)::int AS total,
       count(*) FILTER (WHERE max_seed_risk_score >= %s)::int AS flagged
FROM provider_features
"""

# Blind scoring: subtract revocation signal for revoked providers.
# Uses REVOCATION_RISK_POINTS constant so this stays in sync with taxonomy.
_BLIND_CASE = f"""CASE WHEN revoked_2026 = 1
                THEN GREATEST(max_seed_risk_score - {REVOCATION_RISK_POINTS}, 0)
                ELSE max_seed_risk_score
           END"""

_BLIND_STATE_SQL = f"""
SELECT state AS cohort,
       count(*)::int AS provider_count,
       count(*) FILTER (WHERE {_BLIND_CASE} >= %s)::int AS flagged_count
FROM provider_features
WHERE state IS NOT NULL
GROUP BY state
ORDER BY state
"""

_BLIND_SPECIALTY_SQL = f"""
SELECT provider_type AS cohort,
       count(*)::int AS provider_count,
       count(*) FILTER (WHERE {_BLIND_CASE} >= %s)::int AS flagged_count
FROM provider_features
WHERE provider_type IS NOT NULL
GROUP BY provider_type
ORDER BY provider_type
"""

_BLIND_OVERALL_SQL = f"""
SELECT count(*)::int AS total,
       count(*) FILTER (WHERE {_BLIND_CASE} >= %s)::int AS flagged
FROM provider_features
"""


def _build_cohorts(rows: list[dict], overall_rate: float, std_rate: float) -> list[CohortFairness]:
    """Convert raw rows into CohortFairness with outlier detection."""
    cohorts: list[CohortFairness] = []
    for r in rows:
        count = r["provider_count"]
        flagged = r["flagged_count"]
        rate = flagged / count if count > 0 else 0.0
        is_outlier = (rate - overall_rate) > 2 * std_rate if std_rate > 0 else False
        cohorts.append(
            CohortFairness(
                cohort=r["cohort"],
                provider_count=count,
                flagged_count=flagged,
                flagging_rate=round(rate, 4),
                is_outlier=is_outlier,
            )
        )
    return cohorts


def _compute_parity(
    cohorts: list[CohortFairness],
) -> tuple[float | None, float | None]:
    """Compute statistical parity difference and disparate impact ratio.

    Statistical parity difference: max(rate) - min(rate)
    Disparate impact ratio: min(rate) / max(rate)  (1.0 = perfect parity)
    """
    rates = [c.flagging_rate for c in cohorts if c.provider_count > 0]
    if len(rates) < 2:
        return None, None
    max_rate = max(rates)
    min_rate = min(rates)
    spd = round(max_rate - min_rate, 4)
    di = round(min_rate / max_rate, 4) if max_rate > 0 else None
    return spd, di


def _std_of_rates(rows: list[dict]) -> float:
    """Population standard deviation of flagging rates across cohorts."""
    rates = [r["flagged_count"] / r["provider_count"] for r in rows if r["provider_count"] > 0]
    if len(rates) < 2:
        return 0.0
    mean = sum(rates) / len(rates)
    variance = sum((r - mean) ** 2 for r in rates) / len(rates)
    return math.sqrt(variance)


@router.get("", response_model=FairnessReport)
async def get_fairness(
    threshold: int = Query(DEFAULT_THRESHOLD, ge=0, le=100),
    blind: bool = Query(False, description="If true, exclude revocation signal from scoring"),
    conn: AsyncConnection = Depends(get_db),
) -> FairnessReport:
    """Compute fairness metrics across geography and specialty.

    When blind=true, scores are adjusted to remove the revocation signal,
    showing how the system performs on behavioral signals alone. This also
    returns a revocation_impact comparison.
    """
    state_sql = _BLIND_STATE_SQL if blind else _STATE_SQL
    specialty_sql = _BLIND_SPECIALTY_SQL if blind else _SPECIALTY_SQL
    overall_sql = _BLIND_OVERALL_SQL if blind else _OVERALL_SQL

    async with conn.cursor(row_factory=dict_row) as cur:
        # Overall flagging rate
        await cur.execute(overall_sql, [threshold])
        overall = await cur.fetchone()
        total = overall["total"] if overall else 0
        flagged = overall["flagged"] if overall else 0
        overall_rate = flagged / total if total > 0 else 0.0

        # By state
        await cur.execute(state_sql, [threshold])
        state_rows = await cur.fetchall()

        # By specialty
        await cur.execute(specialty_sql, [threshold])
        specialty_rows = await cur.fetchall()

        # Revocation impact comparison (always compute when blind=true)
        revocation_impact = None
        if blind:
            # Get non-blind rates for comparison
            await cur.execute(_OVERALL_SQL, [threshold])
            orig_overall = await cur.fetchone()
            orig_flagged = orig_overall["flagged"] if orig_overall else 0
            orig_rate = orig_flagged / total if total > 0 else 0.0

            await cur.execute(_STATE_SQL, [threshold])
            orig_state_rows = await cur.fetchall()
            orig_state_std = _std_of_rates(orig_state_rows)
            orig_by_state = _build_cohorts(orig_state_rows, orig_rate, orig_state_std)
            _, orig_di = _compute_parity(orig_by_state)

    state_std = _std_of_rates(state_rows)
    specialty_std = _std_of_rates(specialty_rows)

    by_state = _build_cohorts(state_rows, overall_rate, state_std)
    by_specialty = _build_cohorts(specialty_rows, overall_rate, specialty_std)

    spd_state, di_state = _compute_parity(by_state)
    spd_spec, di_spec = _compute_parity(by_specialty)

    spd = max((x for x in [spd_state, spd_spec] if x is not None), default=None)
    di = min((x for x in [di_state, di_spec] if x is not None), default=None)

    if blind:
        revocation_impact = RevocationImpact(
            overall_flagging_rate_with=round(orig_rate, 4),
            overall_flagging_rate_without=round(overall_rate, 4),
            flagging_rate_delta=round(overall_rate - orig_rate, 4),
            disparate_impact_with=orig_di,
            disparate_impact_without=di,
        )

    return FairnessReport(
        by_state=by_state,
        by_specialty=by_specialty,
        overall_flagging_rate=round(overall_rate, 4),
        statistical_parity_diff=spd,
        disparate_impact_ratio=di,
        revocation_impact=revocation_impact,
    )
