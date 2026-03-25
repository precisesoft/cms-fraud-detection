"""Postgres ETL pipeline — port of the DuckDB ``build_demo_case_csv.py`` logic.

Reads from the four ``raw_*`` tables (loaded by :mod:`src.pipeline.raw_loader`),
joins them, computes peer baselines, z-scores, and seed scoring rules, then
upserts results into ``provider_service_cases``.

Stages
------
1. :func:`run_stage_ingest`         — join raw sources, compute derived ratios
2. :func:`run_stage_peer_baselines` — state + national peer statistics
3. :func:`run_stage_zscores`        — 4 z-scores from peer baselines
4. :func:`run_stage_seed_scoring`   — scores, labels, reasons → upsert

All scoring thresholds and point values are imported from
:mod:`src.scoring.taxonomy` — that module is the **single source of truth**.

Config
------
Set ``PIPELINE_SAMPLE_LIMIT`` in the environment to cap the total rows written
to ``provider_service_cases`` in demo mode.  No limit is applied by default.

    PIPELINE_SAMPLE_LIMIT=20000 python -m src.pipeline.etl
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.scoring.taxonomy import (
    CHARGE_RATIO_OUTLIER,
    ENROLLED_CURRENT,
    HIGH_RISK_GAP,
    HIGH_RISK_SCORE_THRESHOLD,
    LARGE_PATIENT_PANEL,
    MEDICARE_PARTICIPATING,
    MIN_PEER_COUNT,
    NO_REVOCATION,
    NOT_IN_ENROLLMENT,
    PAYMENT_OUTLIER,
    PEER_ALIGNED_INTENSITY,
    PEER_ALIGNED_PRICING,
    PEER_ALIGNED_VOLUME,
    REVOKED_PROVIDER,
    SCORE_CAP,
    SERVICE_INTENSITY_OUTLIER,
    SERVICE_VOLUME_OUTLIER,
    STABLE_LEGITIMACY_THRESHOLD,
    STABLE_RISK_CEILING,
)

if TYPE_CHECKING:
    import psycopg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _parse_sample_limit() -> int | None:
    raw = os.environ.get("PIPELINE_SAMPLE_LIMIT")
    if raw is None:
        return None
    return int(raw)


PIPELINE_SAMPLE_LIMIT: int | None = _parse_sample_limit()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SourceVersions:
    """Source version strings for the four raw CMS tables."""

    service: str
    provider: str
    enrollment: str
    revocations: str


@dataclass
class StageResult:
    """Metrics returned by each pipeline stage."""

    stage: str
    row_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SQL helpers — build tiered CASE expressions from taxonomy definitions
# ---------------------------------------------------------------------------


def _z_risk_case(col: str, signal: Any) -> str:
    """Return a SQL ``CASE`` fragment for a tiered z-score risk signal.

    Uses the signal's ``z_tiers`` (ordered highest-first) to build a
    ``CASE WHEN peer_case_count >= MIN_PEER_COUNT AND col >= z_min THEN points``
    expression that matches the taxonomy exactly.
    """
    parts = [
        f"WHEN peer_case_count >= {MIN_PEER_COUNT} AND {col} >= {tier.z_min} THEN {tier.points}"
        for tier in signal.z_tiers
    ]
    parts.append("ELSE 0")
    return "CASE\n        " + "\n        ".join(parts) + "\n      END"


def _peer_select_case(state_col: str, national_col: str) -> str:
    """Return a SQL ``CASE`` that picks state peer value when count >= MIN_PEER_COUNT."""
    return (
        f"CASE WHEN COALESCE(ps.peer_case_count_state, 0) >= {MIN_PEER_COUNT} "
        f"THEN {state_col} ELSE {national_col} END"
    )


# ---------------------------------------------------------------------------
# Stage 1 — Ingest: join raw sources → _etl_base
# ---------------------------------------------------------------------------

_SQL_DROP_BASE = "DROP TABLE IF EXISTS _etl_base"

_SQL_CREATE_BASE = """\
CREATE TEMP TABLE _etl_base AS
WITH
service AS (
  SELECT
    npi,
    provider_last_org_name,
    provider_first_name,
    provider_credentials,
    provider_entity_code,
    provider_city,
    provider_state,
    provider_zip5,
    provider_type,
    medicare_participating_ind,
    hcpcs_cd,
    hcpcs_desc,
    place_of_service,
    tot_benes,
    tot_srvcs,
    tot_bene_day_srvcs,
    avg_submitted_charge,
    avg_medicare_allowed_amt,
    avg_medicare_payment_amt
  FROM raw_part_b_service
  WHERE source_version = %s
    AND tot_benes  >= 11
    AND tot_srvcs  >= 11
    AND avg_medicare_allowed_amt > 0
),
provider AS (
  SELECT
    npi,
    total_hcpcs_codes  AS provider_total_hcpcs_codes,
    total_benes        AS provider_total_benes,
    total_services     AS provider_total_services,
    total_payment_amt  AS provider_total_payment_amt
  FROM raw_part_b_provider
  WHERE source_version = %s
),
enrollment AS (
  SELECT
    npi,
    1                             AS present_in_2025_enrollment_file,
    COUNT(DISTINCT enrollment_id) AS enrollment_record_count,
    MIN(provider_type_desc)       AS enrollment_provider_type_desc,
    MIN(state_cd)                 AS enrollment_state_cd
  FROM raw_enrollment
  WHERE source_version = %s
  GROUP BY 1
),
revoked AS (
  SELECT
    npi,
    1                                              AS present_in_2026_revocation_file,
    STRING_AGG(DISTINCT revocation_reason, ' | ') AS revocation_reason_summary
  FROM raw_revocations
  WHERE source_version = %s
  GROUP BY 1
)
SELECT
  CONCAT_WS('|', s.npi, s.hcpcs_cd, s.place_of_service) AS case_id,
  s.npi,
  s.provider_last_org_name,
  s.provider_first_name,
  s.provider_credentials,
  s.provider_entity_code,
  s.provider_city,
  s.provider_state,
  s.provider_zip5,
  s.provider_type,
  s.medicare_participating_ind,
  s.hcpcs_cd,
  s.hcpcs_desc,
  s.place_of_service,
  s.tot_benes,
  s.tot_srvcs,
  s.tot_bene_day_srvcs,
  s.avg_submitted_charge,
  s.avg_medicare_allowed_amt,
  s.avg_medicare_payment_amt,
  p.provider_total_hcpcs_codes,
  p.provider_total_benes,
  p.provider_total_services,
  p.provider_total_payment_amt,
  COALESCE(e.present_in_2025_enrollment_file, 0)  AS present_in_2025_enrollment_file,
  COALESCE(e.enrollment_record_count, 0)           AS enrollment_record_count,
  e.enrollment_provider_type_desc,
  e.enrollment_state_cd,
  COALESCE(r.present_in_2026_revocation_file, 0)   AS present_in_2026_revocation_file,
  r.revocation_reason_summary,
  ROUND(s.tot_srvcs / NULLIF(s.tot_benes, 0), 4)                                AS services_per_bene,
  ROUND(s.avg_submitted_charge / NULLIF(s.avg_medicare_allowed_amt, 0), 4)       AS submitted_to_allowed_ratio,
  ROUND(s.avg_medicare_payment_amt / NULLIF(s.avg_medicare_allowed_amt, 0), 4)   AS payment_to_allowed_ratio,
  ROUND(s.tot_srvcs * s.avg_medicare_payment_amt, 2)                             AS estimated_case_payment_amt
FROM service s
LEFT JOIN provider   p USING (npi)
LEFT JOIN enrollment e USING (npi)
LEFT JOIN revoked    r USING (npi)\
"""


def run_stage_ingest(
    conn: psycopg.Connection,  # type: ignore[name-defined]
    versions: SourceVersions,
    *,
    run_id: str | None = None,
) -> StageResult:
    """Stage 1 — join the four raw sources into ``_etl_base``.

    Filters service rows to those with ``tot_benes >= 11``,
    ``tot_srvcs >= 11``, and ``avg_medicare_allowed_amt > 0``.
    Computes ``services_per_bene``, ``submitted_to_allowed_ratio``,
    ``payment_to_allowed_ratio``, and ``estimated_case_payment_amt``.
    ``case_id`` is ``CONCAT_WS('|', npi, hcpcs_cd, place_of_service)``.

    Args:
        conn: Open sync psycopg connection.
        versions: Source version strings for the four raw tables.
        run_id: Optional pipeline run identifier for log context.

    Returns:
        :class:`StageResult` with the number of rows written to ``_etl_base``.
    """
    prefix = f"[{run_id}] " if run_id else ""
    logger.info("%sStage 1 — ingest", prefix)

    conn.execute(_SQL_DROP_BASE)
    conn.execute(
        _SQL_CREATE_BASE,
        [versions.service, versions.provider, versions.enrollment, versions.revocations],
    )
    row = conn.execute("SELECT COUNT(*) FROM _etl_base").fetchone()
    count = int(row[0]) if row else 0
    logger.info("%sStage 1 complete — %d base rows", prefix, count)
    return StageResult(stage="ingest", row_count=count)


# ---------------------------------------------------------------------------
# Stage 2 — Peer baselines: state + national → _etl_peers
# ---------------------------------------------------------------------------

_SQL_DROP_PEERS = "DROP TABLE IF EXISTS _etl_peers"

_SQL_CREATE_PEERS = f"""\
CREATE TEMP TABLE _etl_peers AS
WITH
peer_state AS (
  SELECT
    provider_type,
    provider_state,
    hcpcs_cd,
    place_of_service,
    COUNT(*)                               AS peer_case_count_state,
    AVG(tot_srvcs)                         AS peer_avg_tot_srvcs_state,
    STDDEV_POP(tot_srvcs)                  AS peer_std_tot_srvcs_state,
    AVG(services_per_bene)                 AS peer_avg_services_per_bene_state,
    STDDEV_POP(services_per_bene)          AS peer_std_services_per_bene_state,
    AVG(submitted_to_allowed_ratio)        AS peer_avg_charge_ratio_state,
    STDDEV_POP(submitted_to_allowed_ratio) AS peer_std_charge_ratio_state,
    AVG(avg_medicare_payment_amt)          AS peer_avg_payment_state,
    STDDEV_POP(avg_medicare_payment_amt)   AS peer_std_payment_state
  FROM _etl_base
  GROUP BY 1, 2, 3, 4
),
peer_national AS (
  SELECT
    provider_type,
    hcpcs_cd,
    place_of_service,
    COUNT(*)                               AS peer_case_count_national,
    AVG(tot_srvcs)                         AS peer_avg_tot_srvcs_national,
    STDDEV_POP(tot_srvcs)                  AS peer_std_tot_srvcs_national,
    AVG(services_per_bene)                 AS peer_avg_services_per_bene_national,
    STDDEV_POP(services_per_bene)          AS peer_std_services_per_bene_national,
    AVG(submitted_to_allowed_ratio)        AS peer_avg_charge_ratio_national,
    STDDEV_POP(submitted_to_allowed_ratio) AS peer_std_charge_ratio_national,
    AVG(avg_medicare_payment_amt)          AS peer_avg_payment_national,
    STDDEV_POP(avg_medicare_payment_amt)   AS peer_std_payment_national
  FROM _etl_base
  GROUP BY 1, 2, 3
)
SELECT
  b.*,
  CASE WHEN COALESCE(ps.peer_case_count_state, 0) >= {MIN_PEER_COUNT}
       THEN 'state_specific' ELSE 'national_fallback' END            AS peer_scope,
  {_peer_select_case("ps.peer_case_count_state", "pn.peer_case_count_national")}
                                                                     AS peer_case_count,
  {_peer_select_case("ps.peer_avg_tot_srvcs_state", "pn.peer_avg_tot_srvcs_national")}
                                                                     AS peer_avg_tot_srvcs,
  {_peer_select_case("ps.peer_std_tot_srvcs_state", "pn.peer_std_tot_srvcs_national")}
                                                                     AS peer_std_tot_srvcs,
  {_peer_select_case("ps.peer_avg_services_per_bene_state", "pn.peer_avg_services_per_bene_national")}
                                                                     AS peer_avg_services_per_bene,
  {_peer_select_case("ps.peer_std_services_per_bene_state", "pn.peer_std_services_per_bene_national")}
                                                                     AS peer_std_services_per_bene,
  {_peer_select_case("ps.peer_avg_charge_ratio_state", "pn.peer_avg_charge_ratio_national")}
                                                                     AS peer_avg_charge_ratio,
  {_peer_select_case("ps.peer_std_charge_ratio_state", "pn.peer_std_charge_ratio_national")}
                                                                     AS peer_std_charge_ratio,
  {_peer_select_case("ps.peer_avg_payment_state", "pn.peer_avg_payment_national")}
                                                                     AS peer_avg_payment,
  {_peer_select_case("ps.peer_std_payment_state", "pn.peer_std_payment_national")}
                                                                     AS peer_std_payment
FROM _etl_base b
LEFT JOIN peer_state ps
  ON  b.provider_type   = ps.provider_type
  AND b.provider_state  = ps.provider_state
  AND b.hcpcs_cd        = ps.hcpcs_cd
  AND b.place_of_service = ps.place_of_service
LEFT JOIN peer_national pn
  ON  b.provider_type    = pn.provider_type
  AND b.hcpcs_cd         = pn.hcpcs_cd
  AND b.place_of_service = pn.place_of_service\
"""


def run_stage_peer_baselines(
    conn: psycopg.Connection,  # type: ignore[name-defined]
    *,
    run_id: str | None = None,
) -> StageResult:
    """Stage 2 — compute state and national peer statistics into ``_etl_peers``.

    State peers are used when the count is ``>= MIN_PEER_COUNT``; otherwise
    national baselines are the fallback.  Each peer group covers the
    ``(provider_type, hcpcs_cd, place_of_service)`` combination, and state
    peers additionally include ``provider_state``.

    Reads from ``_etl_base`` (created by :func:`run_stage_ingest`).

    Args:
        conn: Open sync psycopg connection (same session as stage 1).
        run_id: Optional pipeline run identifier for log context.

    Returns:
        :class:`StageResult` with row count and the number of distinct peer
        groups (state and national) found.
    """
    prefix = f"[{run_id}] " if run_id else ""
    logger.info("%sStage 2 — peer baselines", prefix)

    conn.execute(_SQL_DROP_PEERS)
    conn.execute(_SQL_CREATE_PEERS)
    row = conn.execute("SELECT COUNT(*) FROM _etl_peers").fetchone()
    count = int(row[0]) if row else 0

    state_row = conn.execute(
        "SELECT COUNT(DISTINCT (provider_type, provider_state, hcpcs_cd, place_of_service)) "
        "FROM _etl_peers WHERE peer_scope = 'state_specific'"
    ).fetchone()
    national_row = conn.execute(
        "SELECT COUNT(DISTINCT (provider_type, hcpcs_cd, place_of_service)) "
        "FROM _etl_peers WHERE peer_scope = 'national_fallback'"
    ).fetchone()
    n_state = int(state_row[0]) if state_row else 0
    n_national = int(national_row[0]) if national_row else 0

    logger.info(
        "%sStage 2 complete — %d rows, %d state groups, %d national fallback groups",
        prefix,
        count,
        n_state,
        n_national,
    )
    return StageResult(
        stage="peer_baselines",
        row_count=count,
        extra={"n_state_groups": n_state, "n_national_groups": n_national},
    )


# ---------------------------------------------------------------------------
# Stage 3 — Z-scores: 4 z-scores → _etl_zscored
# ---------------------------------------------------------------------------

_SQL_DROP_ZSCORED = "DROP TABLE IF EXISTS _etl_zscored"

_SQL_CREATE_ZSCORED = """\
CREATE TEMP TABLE _etl_zscored AS
SELECT
  *,
  ROUND(
    CASE WHEN COALESCE(peer_std_tot_srvcs, 0) = 0 THEN 0
         ELSE (tot_srvcs - peer_avg_tot_srvcs) / peer_std_tot_srvcs END,
    4
  ) AS service_volume_peer_z,
  ROUND(
    CASE WHEN COALESCE(peer_std_services_per_bene, 0) = 0 THEN 0
         ELSE (services_per_bene - peer_avg_services_per_bene) / peer_std_services_per_bene END,
    4
  ) AS services_per_bene_peer_z,
  ROUND(
    CASE WHEN COALESCE(peer_std_charge_ratio, 0) = 0 THEN 0
         ELSE (submitted_to_allowed_ratio - peer_avg_charge_ratio) / peer_std_charge_ratio END,
    4
  ) AS submitted_to_allowed_peer_z,
  ROUND(
    CASE WHEN COALESCE(peer_std_payment, 0) = 0 THEN 0
         ELSE (avg_medicare_payment_amt - peer_avg_payment) / peer_std_payment END,
    4
  ) AS payment_peer_z
FROM _etl_peers\
"""


def run_stage_zscores(
    conn: psycopg.Connection,  # type: ignore[name-defined]
    *,
    run_id: str | None = None,
) -> StageResult:
    """Stage 3 — compute 4 peer-comparison z-scores into ``_etl_zscored``.

    Z-scores computed:

    * ``service_volume_peer_z``      — (tot_srvcs - peer_avg) / peer_std
    * ``services_per_bene_peer_z``   — (services_per_bene - peer_avg) / peer_std
    * ``submitted_to_allowed_peer_z`` — (charge_ratio - peer_avg) / peer_std
    * ``payment_peer_z``             — (avg_payment - peer_avg) / peer_std

    Defaults to 0 when peer_std is 0 or NULL.

    Reads from ``_etl_peers`` (created by :func:`run_stage_peer_baselines`).

    Args:
        conn: Open sync psycopg connection (same session as prior stages).
        run_id: Optional pipeline run identifier for log context.

    Returns:
        :class:`StageResult` with row count.
    """
    prefix = f"[{run_id}] " if run_id else ""
    logger.info("%sStage 3 — z-scores", prefix)

    conn.execute(_SQL_DROP_ZSCORED)
    conn.execute(_SQL_CREATE_ZSCORED)
    row = conn.execute("SELECT COUNT(*) FROM _etl_zscored").fetchone()
    count = int(row[0]) if row else 0
    logger.info("%sStage 3 complete — %d z-scored rows", prefix, count)
    return StageResult(stage="zscores", row_count=count)


# ---------------------------------------------------------------------------
# Stage 4 — Seed scoring + upsert → provider_service_cases
# ---------------------------------------------------------------------------

# Risk score SQL fragment — built from taxonomy constants
_RISK_SCORE_SQL = f"""\
LEAST(
      {SCORE_CAP},
      CASE WHEN present_in_2026_revocation_file = 1 THEN {REVOKED_PROVIDER.points} ELSE 0 END
      + CASE WHEN present_in_2025_enrollment_file = 0 THEN {NOT_IN_ENROLLMENT.points} ELSE 0 END
      + {_z_risk_case("service_volume_peer_z", SERVICE_VOLUME_OUTLIER)}
      + {_z_risk_case("services_per_bene_peer_z", SERVICE_INTENSITY_OUTLIER)}
      + {_z_risk_case("submitted_to_allowed_peer_z", CHARGE_RATIO_OUTLIER)}
      + {_z_risk_case("payment_peer_z", PAYMENT_OUTLIER)}
    )\
"""

# Legitimacy score SQL fragment — built from taxonomy constants
_LEGITIMACY_SCORE_SQL = f"""\
LEAST(
      {SCORE_CAP},
      CASE WHEN present_in_2025_enrollment_file = 1 THEN {ENROLLED_CURRENT.points} ELSE 0 END
      + CASE WHEN present_in_2026_revocation_file = 0 THEN {NO_REVOCATION.points} ELSE 0 END
      + CASE WHEN medicare_participating_ind = 'Y' THEN {MEDICARE_PARTICIPATING.points} ELSE 0 END
      + CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
              AND ABS(service_volume_peer_z) < {PEER_ALIGNED_VOLUME.threshold}
             THEN {PEER_ALIGNED_VOLUME.points} ELSE 0 END
      + CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
              AND ABS(services_per_bene_peer_z) < {PEER_ALIGNED_INTENSITY.threshold}
             THEN {PEER_ALIGNED_INTENSITY.points} ELSE 0 END
      + CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
              AND ABS(submitted_to_allowed_peer_z) < {PEER_ALIGNED_PRICING.threshold}
             THEN {PEER_ALIGNED_PRICING.points} ELSE 0 END
      + CASE WHEN COALESCE(provider_total_benes, 0) >= {LARGE_PATIENT_PANEL.threshold}
             THEN {LARGE_PATIENT_PANEL.points} ELSE 0 END
    )\
"""

# Case label SQL fragment — built from taxonomy constants
_LABEL_SQL = f"""\
CASE
      WHEN seed_risk_score >= {HIGH_RISK_SCORE_THRESHOLD}
       AND seed_risk_score >= seed_legitimacy_score + {HIGH_RISK_GAP}
      THEN 'high_risk'
      WHEN seed_legitimacy_score >= {STABLE_LEGITIMACY_THRESHOLD}
       AND seed_risk_score < {STABLE_RISK_CEILING}
      THEN 'stable'
      ELSE 'review'
    END\
"""

# Risk reason string — signals with z_reason_threshold >= threshold
_RISK_REASONS_SQL = f"""\
CONCAT_WS(
      '|',
      CASE WHEN present_in_2026_revocation_file = 1
           THEN '{REVOKED_PROVIDER.name}' END,
      CASE WHEN present_in_2025_enrollment_file = 0
           THEN '{NOT_IN_ENROLLMENT.name}' END,
      CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
            AND service_volume_peer_z >= {SERVICE_VOLUME_OUTLIER.z_reason_threshold}
           THEN '{SERVICE_VOLUME_OUTLIER.name}' END,
      CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
            AND services_per_bene_peer_z >= {SERVICE_INTENSITY_OUTLIER.z_reason_threshold}
           THEN '{SERVICE_INTENSITY_OUTLIER.name}' END,
      CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
            AND submitted_to_allowed_peer_z >= {CHARGE_RATIO_OUTLIER.z_reason_threshold}
           THEN '{CHARGE_RATIO_OUTLIER.name}' END,
      CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
            AND payment_peer_z >= {PAYMENT_OUTLIER.z_reason_threshold}
           THEN '{PAYMENT_OUTLIER.name}' END
    )\
"""

# Legitimacy reason string
_LEGITIMACY_REASONS_SQL = f"""\
CONCAT_WS(
      '|',
      CASE WHEN present_in_2025_enrollment_file = 1
           THEN '{ENROLLED_CURRENT.name}' END,
      CASE WHEN present_in_2026_revocation_file = 0
           THEN '{NO_REVOCATION.name}' END,
      CASE WHEN medicare_participating_ind = 'Y'
           THEN '{MEDICARE_PARTICIPATING.name}' END,
      CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
            AND ABS(service_volume_peer_z) < {PEER_ALIGNED_VOLUME.threshold}
           THEN '{PEER_ALIGNED_VOLUME.name}' END,
      CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
            AND ABS(services_per_bene_peer_z) < {PEER_ALIGNED_INTENSITY.threshold}
           THEN '{PEER_ALIGNED_INTENSITY.name}' END,
      CASE WHEN peer_case_count >= {MIN_PEER_COUNT}
            AND ABS(submitted_to_allowed_peer_z) < {PEER_ALIGNED_PRICING.threshold}
           THEN '{PEER_ALIGNED_PRICING.name}' END
    )\
"""

# Columns in final output (preserving order from build_demo_case_csv.py)
_UPSERT_COLUMNS = """\
  case_id,
  npi,
  provider_last_org_name,
  provider_first_name,
  provider_credentials,
  provider_entity_code,
  provider_city,
  provider_state,
  provider_zip5,
  provider_type,
  medicare_participating_ind,
  hcpcs_cd,
  hcpcs_desc,
  place_of_service,
  tot_benes,
  tot_srvcs,
  tot_bene_day_srvcs,
  avg_submitted_charge,
  avg_medicare_allowed_amt,
  avg_medicare_payment_amt,
  estimated_case_payment_amt,
  services_per_bene,
  submitted_to_allowed_ratio,
  payment_to_allowed_ratio,
  provider_total_hcpcs_codes,
  provider_total_benes,
  provider_total_services,
  provider_total_payment_amt,
  present_in_2025_enrollment_file,
  enrollment_record_count,
  enrollment_provider_type_desc,
  enrollment_state_cd,
  present_in_2026_revocation_file,
  revocation_reason_summary,
  peer_scope,
  peer_case_count,
  peer_avg_tot_srvcs,
  service_volume_peer_z,
  services_per_bene_peer_z,
  submitted_to_allowed_peer_z,
  payment_peer_z,
  seed_risk_score,
  seed_legitimacy_score,
  seed_case_label,
  seed_risk_reasons,
  seed_legitimacy_reasons\
"""

_UPSERT_UPDATE_SET = """\
  npi                           = EXCLUDED.npi,
  provider_last_org_name        = EXCLUDED.provider_last_org_name,
  provider_first_name           = EXCLUDED.provider_first_name,
  provider_credentials          = EXCLUDED.provider_credentials,
  provider_entity_code          = EXCLUDED.provider_entity_code,
  provider_city                 = EXCLUDED.provider_city,
  provider_state                = EXCLUDED.provider_state,
  provider_zip5                 = EXCLUDED.provider_zip5,
  provider_type                 = EXCLUDED.provider_type,
  medicare_participating_ind    = EXCLUDED.medicare_participating_ind,
  hcpcs_cd                      = EXCLUDED.hcpcs_cd,
  hcpcs_desc                    = EXCLUDED.hcpcs_desc,
  place_of_service              = EXCLUDED.place_of_service,
  tot_benes                     = EXCLUDED.tot_benes,
  tot_srvcs                     = EXCLUDED.tot_srvcs,
  tot_bene_day_srvcs            = EXCLUDED.tot_bene_day_srvcs,
  avg_submitted_charge          = EXCLUDED.avg_submitted_charge,
  avg_medicare_allowed_amt      = EXCLUDED.avg_medicare_allowed_amt,
  avg_medicare_payment_amt      = EXCLUDED.avg_medicare_payment_amt,
  estimated_case_payment_amt    = EXCLUDED.estimated_case_payment_amt,
  services_per_bene             = EXCLUDED.services_per_bene,
  submitted_to_allowed_ratio    = EXCLUDED.submitted_to_allowed_ratio,
  payment_to_allowed_ratio      = EXCLUDED.payment_to_allowed_ratio,
  provider_total_hcpcs_codes    = EXCLUDED.provider_total_hcpcs_codes,
  provider_total_benes          = EXCLUDED.provider_total_benes,
  provider_total_services       = EXCLUDED.provider_total_services,
  provider_total_payment_amt    = EXCLUDED.provider_total_payment_amt,
  present_in_2025_enrollment_file = EXCLUDED.present_in_2025_enrollment_file,
  enrollment_record_count       = EXCLUDED.enrollment_record_count,
  enrollment_provider_type_desc = EXCLUDED.enrollment_provider_type_desc,
  enrollment_state_cd           = EXCLUDED.enrollment_state_cd,
  present_in_2026_revocation_file = EXCLUDED.present_in_2026_revocation_file,
  revocation_reason_summary     = EXCLUDED.revocation_reason_summary,
  peer_scope                    = EXCLUDED.peer_scope,
  peer_case_count               = EXCLUDED.peer_case_count,
  peer_avg_tot_srvcs            = EXCLUDED.peer_avg_tot_srvcs,
  service_volume_peer_z         = EXCLUDED.service_volume_peer_z,
  services_per_bene_peer_z      = EXCLUDED.services_per_bene_peer_z,
  submitted_to_allowed_peer_z   = EXCLUDED.submitted_to_allowed_peer_z,
  payment_peer_z                = EXCLUDED.payment_peer_z,
  seed_risk_score               = EXCLUDED.seed_risk_score,
  seed_legitimacy_score         = EXCLUDED.seed_legitimacy_score,
  seed_case_label               = EXCLUDED.seed_case_label,
  seed_risk_reasons             = EXCLUDED.seed_risk_reasons,
  seed_legitimacy_reasons       = EXCLUDED.seed_legitimacy_reasons\
"""


def _build_upsert_sql(sample_limit: int | None = None) -> str:
    """Build the Stage 4 INSERT … ON CONFLICT SQL.

    When *sample_limit* is given, the CTE adds a rank column and the final
    SELECT restricts to the top rows per label (proportional split matching
    the demo-mode ratios: 35% high_risk, 35% review, 30% stable).
    """
    if sample_limit is not None:
        # Proportional split: 35% high_risk, 35% review, 30% stable
        hr_limit = int(sample_limit * 0.35)
        rv_limit = int(sample_limit * 0.35)
        st_limit = sample_limit - hr_limit - rv_limit
        source_cte = f"""\
WITH
scored AS (
  SELECT
    *,
    {_RISK_SCORE_SQL}        AS seed_risk_score,
    {_LEGITIMACY_SCORE_SQL}  AS seed_legitimacy_score
  FROM _etl_zscored
),
labeled AS (
  SELECT *, {_LABEL_SQL} AS seed_case_label FROM scored
),
ranked AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY seed_case_label
      ORDER BY seed_risk_score DESC, estimated_case_payment_amt DESC, npi, hcpcs_cd
    ) AS _sample_rank
  FROM labeled
)
SELECT
{_UPSERT_COLUMNS},
{_RISK_REASONS_SQL}        AS seed_risk_reasons,
{_LEGITIMACY_REASONS_SQL}  AS seed_legitimacy_reasons
FROM ranked
WHERE (seed_case_label = 'high_risk'  AND _sample_rank <= {hr_limit})
   OR (seed_case_label = 'review'     AND _sample_rank <= {rv_limit})
   OR (seed_case_label = 'stable'     AND _sample_rank <= {st_limit})"""
    else:
        source_cte = f"""\
WITH
scored AS (
  SELECT
    *,
    {_RISK_SCORE_SQL}        AS seed_risk_score,
    {_LEGITIMACY_SCORE_SQL}  AS seed_legitimacy_score
  FROM _etl_zscored
),
labeled AS (
  SELECT *, {_LABEL_SQL} AS seed_case_label FROM scored
)
SELECT
{_UPSERT_COLUMNS},
{_RISK_REASONS_SQL}        AS seed_risk_reasons,
{_LEGITIMACY_REASONS_SQL}  AS seed_legitimacy_reasons
FROM labeled"""

    return f"""\
INSERT INTO provider_service_cases (
{_UPSERT_COLUMNS},
  seed_risk_reasons,
  seed_legitimacy_reasons
)
{source_cte}
ON CONFLICT (case_id) DO UPDATE SET
{_UPSERT_UPDATE_SET},
  seed_risk_reasons     = EXCLUDED.seed_risk_reasons,
  seed_legitimacy_reasons = EXCLUDED.seed_legitimacy_reasons\
"""


def run_stage_seed_scoring(
    conn: psycopg.Connection,  # type: ignore[name-defined]
    *,
    run_id: str | None = None,
    sample_limit: int | None = None,
) -> StageResult:
    """Stage 4 — compute seed scores, labels, reasons; upsert into provider_service_cases.

    Scoring thresholds are taken directly from :mod:`src.scoring.taxonomy`:

    * Risk score: ``REVOKED_PROVIDER`` (25 pts), ``NOT_IN_ENROLLMENT`` (8 pts),
      and tiered z-score signals (``SERVICE_VOLUME_OUTLIER``,
      ``SERVICE_INTENSITY_OUTLIER``, ``CHARGE_RATIO_OUTLIER``,
      ``PAYMENT_OUTLIER``), capped at ``SCORE_CAP``.
    * Legitimacy score: enrollment/participation booleans and peer-alignment
      signals, capped at ``SCORE_CAP``.
    * Label: ``high_risk`` when risk >= ``HIGH_RISK_SCORE_THRESHOLD`` and
      risk >= legitimacy + ``HIGH_RISK_GAP``; ``stable`` when
      legitimacy >= ``STABLE_LEGITIMACY_THRESHOLD`` and risk < ``STABLE_RISK_CEILING``;
      otherwise ``review``.

    The upsert uses ``ON CONFLICT (case_id) DO UPDATE`` so existing
    ``case_actions`` referencing stable ``case_id`` values are preserved.

    Args:
        conn: Open sync psycopg connection (same session as prior stages).
        run_id: Optional pipeline run identifier for log context.
        sample_limit: When set, caps total output rows (demo mode).  Uses the
            ``PIPELINE_SAMPLE_LIMIT`` env var if not supplied explicitly.
            Pass ``0`` to explicitly disable sampling.

    Returns:
        :class:`StageResult` with row count and per-label counts.
    """
    prefix = f"[{run_id}] " if run_id else ""
    logger.info("%sStage 4 — seed scoring + upsert", prefix)

    effective_limit: int | None
    if sample_limit is None:
        effective_limit = PIPELINE_SAMPLE_LIMIT
    elif sample_limit == 0:
        effective_limit = None
    else:
        effective_limit = sample_limit

    sql = _build_upsert_sql(effective_limit)
    conn.execute(sql)

    # Gather per-label counts from provider_service_cases
    rows = conn.execute(
        "SELECT seed_case_label, COUNT(*) FROM provider_service_cases GROUP BY 1"
    ).fetchall()
    label_counts = {r[0]: int(r[1]) for r in rows}
    total = sum(label_counts.values())
    logger.info(
        "%sStage 4 complete — %d rows upserted (%s)",
        prefix,
        total,
        ", ".join(f"{k}={v}" for k, v in sorted(label_counts.items())),
    )
    return StageResult(stage="seed_scoring", row_count=total, extra={"label_counts": label_counts})


# ---------------------------------------------------------------------------
# Convenience: run all 4 stages in sequence
# ---------------------------------------------------------------------------


def run_pipeline(
    conn: psycopg.Connection,  # type: ignore[name-defined]
    versions: SourceVersions,
    *,
    run_id: str | None = None,
    sample_limit: int | None = None,
) -> list[StageResult]:
    """Run all four ETL stages in sequence using a single connection.

    Args:
        conn: Open sync psycopg connection.
        versions: Source version strings for the four raw tables.
        run_id: Optional pipeline run identifier for log context.
        sample_limit: See :func:`run_stage_seed_scoring`.

    Returns:
        List of :class:`StageResult` from each stage.
    """
    results = [
        run_stage_ingest(conn, versions, run_id=run_id),
        run_stage_peer_baselines(conn, run_id=run_id),
        run_stage_zscores(conn, run_id=run_id),
        run_stage_seed_scoring(conn, run_id=run_id, sample_limit=sample_limit),
    ]
    return results


# ---------------------------------------------------------------------------
# Pure-Python scoring helper (mirrors Stage 4 SQL — used for tests)
# ---------------------------------------------------------------------------


def compute_seed_scores(
    *,
    present_in_2026_revocation_file: int,
    present_in_2025_enrollment_file: int,
    peer_case_count: int,
    service_volume_peer_z: float,
    services_per_bene_peer_z: float,
    submitted_to_allowed_peer_z: float,
    payment_peer_z: float,
    medicare_participating_ind: str,
    provider_total_benes: float | None,
) -> tuple[int, int]:
    """Compute ``(seed_risk_score, seed_legitimacy_score)`` using taxonomy constants.

    This is the Python equivalent of the Stage 4 SQL scoring expressions.
    It is exposed for unit testing so tests can verify expected scores without
    a live Postgres connection.

    All thresholds and point values are imported from
    :mod:`src.scoring.taxonomy`.

    Returns:
        ``(risk_score, legitimacy_score)`` both capped at ``SCORE_CAP``.
    """
    from src.scoring.taxonomy import points_for_z

    def has_peers(count: int) -> bool:
        return count >= MIN_PEER_COUNT

    risk = 0
    if present_in_2026_revocation_file == 1:
        risk += REVOKED_PROVIDER.points  # type: ignore[operator]
    if present_in_2025_enrollment_file == 0:
        risk += NOT_IN_ENROLLMENT.points  # type: ignore[operator]
    if has_peers(peer_case_count):
        risk += points_for_z(SERVICE_VOLUME_OUTLIER, service_volume_peer_z)
        risk += points_for_z(SERVICE_INTENSITY_OUTLIER, services_per_bene_peer_z)
        risk += points_for_z(CHARGE_RATIO_OUTLIER, submitted_to_allowed_peer_z)
        risk += points_for_z(PAYMENT_OUTLIER, payment_peer_z)
    risk = min(risk, SCORE_CAP)

    legit = 0
    if present_in_2025_enrollment_file == 1:
        legit += ENROLLED_CURRENT.points  # type: ignore[operator]
    if present_in_2026_revocation_file == 0:
        legit += NO_REVOCATION.points  # type: ignore[operator]
    if medicare_participating_ind == "Y":
        legit += MEDICARE_PARTICIPATING.points  # type: ignore[operator]
    if has_peers(peer_case_count):
        vol_threshold = PEER_ALIGNED_VOLUME.threshold
        int_threshold = PEER_ALIGNED_INTENSITY.threshold
        prc_threshold = PEER_ALIGNED_PRICING.threshold
        assert vol_threshold is not None  # always set for peer-aligned signals
        assert int_threshold is not None
        assert prc_threshold is not None
        if abs(service_volume_peer_z) < vol_threshold:
            legit += PEER_ALIGNED_VOLUME.points  # type: ignore[operator]
        if abs(services_per_bene_peer_z) < int_threshold:
            legit += PEER_ALIGNED_INTENSITY.points  # type: ignore[operator]
        if abs(submitted_to_allowed_peer_z) < prc_threshold:
            legit += PEER_ALIGNED_PRICING.points  # type: ignore[operator]
    if (provider_total_benes or 0.0) >= (LARGE_PATIENT_PANEL.threshold or 0.0):
        legit += LARGE_PATIENT_PANEL.points  # type: ignore[operator]
    legit = min(legit, SCORE_CAP)

    return risk, legit


def compute_seed_label(risk_score: int, legitimacy_score: int) -> str:
    """Return the seed case label string matching the Stage 4 SQL CASE expression.

    Uses :mod:`src.scoring.taxonomy` constants as the single source of truth.
    """
    if risk_score >= HIGH_RISK_SCORE_THRESHOLD and risk_score >= legitimacy_score + HIGH_RISK_GAP:
        return "high_risk"
    if legitimacy_score >= STABLE_LEGITIMACY_THRESHOLD and risk_score < STABLE_RISK_CEILING:
        return "stable"
    return "review"
