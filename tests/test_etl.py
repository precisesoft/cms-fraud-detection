"""Tests for src/pipeline/etl.py — Postgres ETL pipeline.

Strategy
--------
Three layers of testing, all without a live database connection:

1. **SQL constants** — verify that the module-level SQL strings contain
   the correct threshold values derived from :mod:`src.scoring.taxonomy`.

2. **Pure-Python scoring helper** — :func:`~src.pipeline.etl.compute_seed_scores`
   and :func:`~src.pipeline.etl.compute_seed_label` implement the same logic
   as the Stage 4 SQL in Python.  We test these with hand-crafted fixture rows
   that cover edge cases (revoked, not-enrolled, outlier z-scores, stable).

3. **Stage function calls** — :func:`~unittest.mock.MagicMock` connections
   verify that each stage function executes the correct SQL statements and
   returns a :class:`~src.pipeline.etl.StageResult` with the expected shape.

No DuckDB dependency.  Expected scores are hardcoded based on taxonomy
constants and manual calculation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.pipeline.etl import (
    _SQL_CREATE_BASE,
    _SQL_CREATE_PEERS,
    _SQL_CREATE_ZSCORED,
    SourceVersions,
    StageResult,
    _build_upsert_sql,
    _z_risk_case,
    compute_seed_label,
    compute_seed_scores,
    run_pipeline,
    run_stage_ingest,
    run_stage_peer_baselines,
    run_stage_seed_scoring,
    run_stage_zscores,
)
from src.scoring.taxonomy import (
    CHARGE_RATIO_OUTLIER,
    ENROLLED_CURRENT,
    HIGH_RISK_GAP,
    HIGH_RISK_SCORE_THRESHOLD,
    LARGE_PATIENT_PANEL,
    MIN_PEER_COUNT,
    NO_REVOCATION,
    NOT_IN_ENROLLMENT,
    PEER_ALIGNED_INTENSITY,
    PEER_ALIGNED_PRICING,
    PEER_ALIGNED_VOLUME,
    REVOKED_PROVIDER,
    SCORE_CAP,
    SERVICE_VOLUME_OUTLIER,
    STABLE_LEGITIMACY_THRESHOLD,
    STABLE_RISK_CEILING,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VERSIONS = SourceVersions(
    service="2023",
    provider="2023",
    enrollment="q4_2025",
    revocations="q1_2026",
)


def _mock_conn(row_count: int = 0) -> MagicMock:
    """Return a MagicMock psycopg connection.

    fetchone() returns (row_count,) so COUNT(*) calls return *row_count*.
    fetchall() returns an empty list (override per test if needed).
    """
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (row_count,)
    conn.execute.return_value.fetchall.return_value = []
    return conn


# ---------------------------------------------------------------------------
# 1. SQL constant correctness
# ---------------------------------------------------------------------------


class TestSqlConstants:
    """Verify that the module-level SQL strings embed the correct constants."""

    def test_ingest_sql_contains_case_id_formula(self):
        """case_id must be CONCAT_WS('|', npi, hcpcs_cd, place_of_service)."""
        assert "CONCAT_WS('|', s.npi, s.hcpcs_cd, s.place_of_service)" in _SQL_CREATE_BASE

    def test_ingest_sql_filters_min_benes(self):
        assert "tot_benes  >= 11" in _SQL_CREATE_BASE

    def test_ingest_sql_filters_min_srvcs(self):
        assert "tot_srvcs  >= 11" in _SQL_CREATE_BASE

    def test_ingest_sql_filters_positive_allowed(self):
        assert "avg_medicare_allowed_amt > 0" in _SQL_CREATE_BASE

    def test_peer_sql_contains_min_peer_count(self):
        """Peer fallback threshold must match taxonomy MIN_PEER_COUNT."""
        assert f">= {MIN_PEER_COUNT}" in _SQL_CREATE_PEERS

    def test_peer_sql_state_specific_label(self):
        assert "state_specific" in _SQL_CREATE_PEERS

    def test_peer_sql_national_fallback_label(self):
        assert "national_fallback" in _SQL_CREATE_PEERS

    def test_zscore_sql_uses_stddev_pop(self):
        assert "STDDEV_POP" in _SQL_CREATE_PEERS

    def test_zscore_sql_zero_when_std_zero(self):
        """Z-scores default to 0 when peer_std is 0 (no division by zero)."""
        assert "COALESCE(peer_std_tot_srvcs, 0) = 0 THEN 0" in _SQL_CREATE_ZSCORED
        assert "COALESCE(peer_std_services_per_bene, 0) = 0 THEN 0" in _SQL_CREATE_ZSCORED
        assert "COALESCE(peer_std_charge_ratio, 0) = 0 THEN 0" in _SQL_CREATE_ZSCORED
        assert "COALESCE(peer_std_payment, 0) = 0 THEN 0" in _SQL_CREATE_ZSCORED

    def test_upsert_sql_contains_on_conflict(self):
        sql = _build_upsert_sql()
        assert "ON CONFLICT (case_id) DO UPDATE" in sql

    def test_upsert_sql_uses_revoked_provider_points(self):
        sql = _build_upsert_sql()
        assert f"THEN {REVOKED_PROVIDER.points}" in sql

    def test_upsert_sql_uses_not_enrolled_points(self):
        sql = _build_upsert_sql()
        assert f"THEN {NOT_IN_ENROLLMENT.points}" in sql

    def test_upsert_sql_uses_high_risk_threshold(self):
        sql = _build_upsert_sql()
        assert f">= {HIGH_RISK_SCORE_THRESHOLD}" in sql

    def test_upsert_sql_uses_high_risk_gap(self):
        sql = _build_upsert_sql()
        assert f"+ {HIGH_RISK_GAP}" in sql

    def test_upsert_sql_uses_stable_legitimacy_threshold(self):
        sql = _build_upsert_sql()
        assert f">= {STABLE_LEGITIMACY_THRESHOLD}" in sql

    def test_upsert_sql_uses_stable_risk_ceiling(self):
        sql = _build_upsert_sql()
        assert f"< {STABLE_RISK_CEILING}" in sql

    def test_upsert_sql_uses_score_cap(self):
        sql = _build_upsert_sql()
        assert f"LEAST(\n      {SCORE_CAP}" in sql

    def test_z_risk_case_embeds_correct_tiers(self):
        """_z_risk_case must embed all z-tier thresholds from the signal."""
        frag = _z_risk_case("service_volume_peer_z", SERVICE_VOLUME_OUTLIER)
        for tier in SERVICE_VOLUME_OUTLIER.z_tiers:
            assert str(tier.z_min) in frag
            assert str(tier.points) in frag

    def test_upsert_sql_uses_peer_aligned_volume_threshold(self):
        sql = _build_upsert_sql()
        assert f"< {PEER_ALIGNED_VOLUME.threshold}" in sql

    def test_upsert_sql_uses_large_panel_threshold(self):
        sql = _build_upsert_sql()
        assert f">= {LARGE_PATIENT_PANEL.threshold}" in sql

    def test_upsert_sql_sample_limit_adds_row_number(self):
        sql = _build_upsert_sql(sample_limit=10000)
        assert "ROW_NUMBER()" in sql
        assert "_sample_rank" in sql

    def test_upsert_sql_no_sample_limit_no_row_number(self):
        sql = _build_upsert_sql(sample_limit=None)
        assert "ROW_NUMBER()" not in sql


# ---------------------------------------------------------------------------
# 2. Pure-Python scoring helper — fixture-based assertions
# ---------------------------------------------------------------------------


class TestComputeSeedScores:
    """Verify compute_seed_scores() matches expected hand-calculated values."""

    # ------------------------------------------------------------------
    # Fixture A — stable provider
    # Enrolled (20), not revoked (15), participating (10)
    # 30 state peers → peer-aligned volume/intensity/pricing (12 + 12 + 12)
    # total benes = 500 → large panel (8)
    # Risk: 0 (no outliers, no flags)
    # Legitimacy: 20 + 15 + 10 + 12 + 12 + 12 + 8 = 89 → capped at 100
    # Expected label: stable (legitimacy >= 70, risk < 30)
    # ------------------------------------------------------------------
    _STABLE = {
        "present_in_2026_revocation_file": 0,
        "present_in_2025_enrollment_file": 1,
        "peer_case_count": 30,
        "service_volume_peer_z": 0.0,
        "services_per_bene_peer_z": 0.0,
        "submitted_to_allowed_peer_z": 0.0,
        "payment_peer_z": 0.0,
        "medicare_participating_ind": "Y",
        "provider_total_benes": 500.0,
    }

    def test_stable_risk_is_zero(self):
        risk, _ = compute_seed_scores(**self._STABLE)
        assert risk == 0

    def test_stable_legitimacy_capped_at_score_cap(self):
        _, legit = compute_seed_scores(**self._STABLE)
        raw = 20 + 15 + 10 + 12 + 12 + 12 + 8  # = 89
        assert legit == min(raw, SCORE_CAP)

    def test_stable_label(self):
        risk, legit = compute_seed_scores(**self._STABLE)
        assert compute_seed_label(risk, legit) == "stable"

    # ------------------------------------------------------------------
    # Fixture B — high-risk provider
    # Revoked (25) + not enrolled (8) + volume z=6 (20) + intensity z=6 (18)
    # + charge z=6 (18) + payment z=6 (12) = 101 → capped at 100
    # Legitimacy: 0 (no_revocation fails, not enrolled, not participating)
    # Expected label: high_risk (risk >= 30, risk >= legitimacy + 5)
    # ------------------------------------------------------------------
    _HIGH_RISK = {
        "present_in_2026_revocation_file": 1,
        "present_in_2025_enrollment_file": 0,
        "peer_case_count": 30,
        "service_volume_peer_z": 6.0,
        "services_per_bene_peer_z": 6.0,
        "submitted_to_allowed_peer_z": 6.0,
        "payment_peer_z": 6.0,
        "medicare_participating_ind": "N",
        "provider_total_benes": 10.0,
    }

    def test_high_risk_risk_capped_at_score_cap(self):
        risk, _ = compute_seed_scores(**self._HIGH_RISK)
        raw = 25 + 8 + 20 + 18 + 18 + 12  # = 101
        assert risk == min(raw, SCORE_CAP)

    def test_high_risk_legitimacy_is_zero(self):
        _, legit = compute_seed_scores(**self._HIGH_RISK)
        assert legit == 0

    def test_high_risk_label(self):
        risk, legit = compute_seed_scores(**self._HIGH_RISK)
        assert compute_seed_label(risk, legit) == "high_risk"

    # ------------------------------------------------------------------
    # Fixture C — review provider
    # Not enrolled (8 risk) + enrolled signal missing (no 20 legit)
    # medium volume z=3 (14 risk) → risk = 22, legitimacy = 15 + 10 = 25
    # Expected label: review
    # ------------------------------------------------------------------
    _REVIEW = {
        "present_in_2026_revocation_file": 0,
        "present_in_2025_enrollment_file": 0,
        "peer_case_count": 30,
        "service_volume_peer_z": 3.0,
        "services_per_bene_peer_z": 0.0,
        "submitted_to_allowed_peer_z": 0.0,
        "payment_peer_z": 0.0,
        "medicare_participating_ind": "Y",
        "provider_total_benes": 50.0,
    }

    def test_review_risk_score(self):
        risk, _ = compute_seed_scores(**self._REVIEW)
        # not_enrolled=8, volume_z=3→14 (tier z>=3.0 gives 14 pts)
        expected_risk = 8 + 14
        assert risk == expected_risk

    def test_review_legitimacy_score(self):
        _, legit = compute_seed_scores(**self._REVIEW)
        # no_revocation=15, participating=10, peer_aligned_intensity=12, pricing=12
        # (volume z=3 ≥ threshold 1.0 → NOT peer_aligned_volume)
        expected_legit = 15 + 10 + 12 + 12  # = 49
        assert legit == expected_legit

    def test_review_label(self):
        risk, legit = compute_seed_scores(**self._REVIEW)
        assert compute_seed_label(risk, legit) == "review"

    # ------------------------------------------------------------------
    # Fixture D — no peers (national fallback with count < 25)
    # peer_case_count = 10 → z-score signals do NOT fire
    # Not revoked, enrolled, participating → legitimacy = 20+15+10 = 45
    # Risk = 0
    # Expected label: review (legit < 70)
    # ------------------------------------------------------------------
    _NO_PEERS = {
        "present_in_2026_revocation_file": 0,
        "present_in_2025_enrollment_file": 1,
        "peer_case_count": 10,
        "service_volume_peer_z": 10.0,
        "services_per_bene_peer_z": 10.0,
        "submitted_to_allowed_peer_z": 10.0,
        "payment_peer_z": 10.0,
        "medicare_participating_ind": "Y",
        "provider_total_benes": 50.0,
    }

    def test_no_peers_risk_score_is_zero(self):
        """Z-score risk signals must not fire when peer_case_count < MIN_PEER_COUNT."""
        risk, _ = compute_seed_scores(**self._NO_PEERS)
        assert risk == 0

    def test_no_peers_legitimacy_no_peer_signals(self):
        """Peer-aligned legitimacy signals must not fire when peer count < MIN_PEER_COUNT."""
        _, legit = compute_seed_scores(**self._NO_PEERS)
        # enrolled=20, no_revocation=15, participating=10 → 45 (no peer signals)
        assert legit == 20 + 15 + 10

    # ------------------------------------------------------------------
    # Fixture E — boundary: exactly MIN_PEER_COUNT peers
    # peer_case_count = 25 → z-score signals SHOULD fire
    # ------------------------------------------------------------------
    def test_exactly_min_peer_count_triggers_peer_signals(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=5.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        # volume z=5 → top tier 20 pts
        assert risk == 20

    def test_one_below_min_peer_count_no_peer_signals(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT - 1,
            service_volume_peer_z=5.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        assert risk == 0

    # ------------------------------------------------------------------
    # Z-tier boundary values
    # ------------------------------------------------------------------

    def test_volume_z_tier_boundary_2(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=2.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        assert risk == 8  # ZTier(2.0, 8)

    def test_volume_z_tier_boundary_3(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=3.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        assert risk == 14  # ZTier(3.0, 14)

    def test_volume_z_tier_boundary_5(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=5.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        assert risk == 20  # ZTier(5.0, 20)

    def test_payment_z_tier_boundary_2(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=2.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        assert risk == 5  # PAYMENT_OUTLIER ZTier(2.0, 5)

    def test_payment_z_tier_boundary_3(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=3.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        assert risk == 8  # PAYMENT_OUTLIER ZTier(3.0, 8)

    def test_payment_z_tier_boundary_5(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=5.0,
            medicare_participating_ind="Y",
            provider_total_benes=50.0,
        )
        assert risk == 12  # PAYMENT_OUTLIER ZTier(5.0, 12)

    def test_peer_aligned_volume_boundary(self):
        """ABS(volume_z) < 1.0 → peer_aligned_volume fires; ABS = 1.0 → does not.

        All other z-scores are 0.0, so they also trigger peer_aligned_intensity
        and peer_aligned_pricing (ABS(0.0) < 1.0).
        """
        # z=0.99: no_revocation(15) + volume(12) + intensity(12) + pricing(12) = 51
        _, legit_below = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=0,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=0.99,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        # z=1.0: no_revocation(15) + intensity(12) + pricing(12) = 39
        # (peer_aligned_volume does NOT fire — ABS(1.0) < 1.0 is False)
        _, legit_at = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=0,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=1.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        assert (
            legit_below
            == NO_REVOCATION.points
            + PEER_ALIGNED_VOLUME.points
            + PEER_ALIGNED_INTENSITY.points
            + PEER_ALIGNED_PRICING.points
        )  # noqa: E501
        assert (
            legit_at
            == NO_REVOCATION.points + PEER_ALIGNED_INTENSITY.points + PEER_ALIGNED_PRICING.points
        )

    def test_large_panel_boundary(self):
        """provider_total_benes >= 100 → LARGE_PATIENT_PANEL fires."""
        _, legit_below = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=0,
            peer_case_count=0,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=99.9,
        )
        _, legit_at = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=0,
            peer_case_count=0,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=100.0,
        )
        assert legit_below == 15  # no_revocation only
        assert legit_at == 15 + 8  # no_revocation + large_panel


class TestComputeSeedLabel:
    """Verify compute_seed_label() boundary conditions match taxonomy."""

    def test_high_risk_boundary(self):
        # risk = HIGH_RISK_SCORE_THRESHOLD, gap = HIGH_RISK_GAP exactly
        risk = HIGH_RISK_SCORE_THRESHOLD
        legit = risk - HIGH_RISK_GAP
        assert compute_seed_label(risk, legit) == "high_risk"

    def test_high_risk_gap_too_small(self):
        risk = HIGH_RISK_SCORE_THRESHOLD
        legit = risk - HIGH_RISK_GAP + 1  # gap < required
        label = compute_seed_label(risk, legit)
        # Could still be review or stable depending on legitimacy value
        assert label != "high_risk"

    def test_stable_boundary(self):
        legit = STABLE_LEGITIMACY_THRESHOLD
        risk = STABLE_RISK_CEILING - 1
        assert compute_seed_label(risk, legit) == "stable"

    def test_stable_risk_at_ceiling_is_review(self):
        legit = STABLE_LEGITIMACY_THRESHOLD
        risk = STABLE_RISK_CEILING  # must be STRICTLY LESS THAN ceiling
        label = compute_seed_label(risk, legit)
        assert label != "stable"

    def test_review_is_default(self):
        assert compute_seed_label(40, 40) == "review"


# ---------------------------------------------------------------------------
# 3. Stage function call verification
# ---------------------------------------------------------------------------


class TestRunStageIngest:
    def test_drops_and_creates_temp_table(self):
        conn = _mock_conn(row_count=5)
        run_stage_ingest(conn, _VERSIONS)
        # First call: DROP TABLE IF EXISTS _etl_base
        first_call_sql = conn.execute.call_args_list[0][0][0]
        assert "_etl_base" in first_call_sql
        assert "DROP" in first_call_sql
        # Second call: CREATE TEMP TABLE _etl_base AS ...
        second_call_sql = conn.execute.call_args_list[1][0][0]
        assert "CREATE TEMP TABLE _etl_base" in second_call_sql

    def test_accepts_versions_and_executes_create(self):
        conn = _mock_conn(row_count=10)
        run_stage_ingest(conn, _VERSIONS)
        # The second call is CREATE TEMP TABLE _etl_base AS ...
        second_call_sql = conn.execute.call_args_list[1][0][0]
        assert "CREATE TEMP TABLE _etl_base" in second_call_sql

    def test_returns_stage_result(self):
        conn = _mock_conn(row_count=42)
        result = run_stage_ingest(conn, _VERSIONS)
        assert isinstance(result, StageResult)
        assert result.stage == "ingest"
        assert result.row_count == 42

    def test_run_id_prefix_in_log(self, caplog):
        import logging

        conn = _mock_conn(row_count=0)
        with caplog.at_level(logging.INFO, logger="src.pipeline.etl"):
            run_stage_ingest(conn, _VERSIONS, run_id="test-run-1")
        assert "test-run-1" in caplog.text


class TestRunStagePeerBaselines:
    def test_drops_and_creates_temp_table(self):
        conn = _mock_conn(row_count=100)
        run_stage_peer_baselines(conn)
        first_call_sql = conn.execute.call_args_list[0][0][0]
        assert "_etl_peers" in first_call_sql
        assert "DROP" in first_call_sql

    def test_returns_stage_result(self):
        conn = _mock_conn(row_count=100)
        result = run_stage_peer_baselines(conn)
        assert isinstance(result, StageResult)
        assert result.stage == "peer_baselines"

    def test_extra_contains_group_counts(self):
        conn = _mock_conn(row_count=100)
        result = run_stage_peer_baselines(conn)
        assert "n_state_groups" in result.extra
        assert "n_national_groups" in result.extra


class TestRunStageZscores:
    def test_drops_and_creates_temp_table(self):
        conn = _mock_conn(row_count=50)
        run_stage_zscores(conn)
        first_call_sql = conn.execute.call_args_list[0][0][0]
        assert "_etl_zscored" in first_call_sql

    def test_returns_stage_result(self):
        conn = _mock_conn(row_count=50)
        result = run_stage_zscores(conn)
        assert isinstance(result, StageResult)
        assert result.stage == "zscores"
        assert result.row_count == 50


class TestRunStageSeedScoring:
    def test_executes_upsert_sql(self):
        conn = _mock_conn(row_count=0)
        run_stage_seed_scoring(conn)
        first_call_sql = conn.execute.call_args_list[0][0][0]
        assert "INSERT INTO provider_service_cases" in first_call_sql
        assert "ON CONFLICT (case_id) DO UPDATE" in first_call_sql

    def test_returns_stage_result(self):
        conn = _mock_conn(row_count=200)
        conn.execute.return_value.fetchall.return_value = [
            ("high_risk", 50),
            ("review", 100),
            ("stable", 50),
        ]
        result = run_stage_seed_scoring(conn)
        assert isinstance(result, StageResult)
        assert result.stage == "seed_scoring"

    def test_sample_limit_zero_disables_sampling(self):
        conn = _mock_conn(row_count=0)
        run_stage_seed_scoring(conn, sample_limit=0)
        sql = conn.execute.call_args_list[0][0][0]
        assert "ROW_NUMBER()" not in sql

    def test_sample_limit_positive_adds_row_number(self):
        conn = _mock_conn(row_count=0)
        run_stage_seed_scoring(conn, sample_limit=1000)
        sql = conn.execute.call_args_list[0][0][0]
        assert "ROW_NUMBER()" in sql

    def test_env_sample_limit_respected(self):
        """When PIPELINE_SAMPLE_LIMIT env is set and no explicit arg, env value is used."""
        conn = _mock_conn(row_count=0)
        with patch("src.pipeline.etl.PIPELINE_SAMPLE_LIMIT", 5000):
            run_stage_seed_scoring(conn)
        sql = conn.execute.call_args_list[0][0][0]
        assert "ROW_NUMBER()" in sql

    def test_label_counts_in_extra(self):
        conn = _mock_conn(row_count=0)
        conn.execute.return_value.fetchall.return_value = [
            ("high_risk", 30),
            ("review", 70),
        ]
        result = run_stage_seed_scoring(conn)
        assert result.extra["label_counts"] == {"high_risk": 30, "review": 70}


class TestRunPipeline:
    def test_runs_all_four_stages(self):
        conn = _mock_conn(row_count=0)
        results = run_pipeline(conn, _VERSIONS)
        assert len(results) == 4
        stage_names = [r.stage for r in results]
        assert stage_names == ["ingest", "peer_baselines", "zscores", "seed_scoring"]

    def test_passes_run_id_to_stages(self, caplog):
        import logging

        conn = _mock_conn(row_count=0)
        with caplog.at_level(logging.INFO, logger="src.pipeline.etl"):
            run_pipeline(conn, _VERSIONS, run_id="pipeline-99")
        assert "pipeline-99" in caplog.text


# ---------------------------------------------------------------------------
# 4. Peer scope fixture — verify state vs. national assignment logic
# ---------------------------------------------------------------------------


class TestPeerScopeAssignment:
    """Verify that peer_scope is assigned correctly at MIN_PEER_COUNT boundary."""

    def test_state_peers_trigger_at_exactly_min_peer_count(self):
        """State peers should be used when count == MIN_PEER_COUNT."""
        sql = _SQL_CREATE_PEERS
        # The SQL should use >= MIN_PEER_COUNT for state selection
        assert f">= {MIN_PEER_COUNT}" in sql
        # Not strictly greater-than
        assert f"> {MIN_PEER_COUNT}" not in sql.replace(f">= {MIN_PEER_COUNT}", "")


# ---------------------------------------------------------------------------
# 5. SourceVersions and StageResult dataclasses
# ---------------------------------------------------------------------------


class TestSourceVersions:
    def test_all_fields_set(self):
        sv = SourceVersions(service="a", provider="b", enrollment="c", revocations="d")
        assert sv.service == "a"
        assert sv.provider == "b"
        assert sv.enrollment == "c"
        assert sv.revocations == "d"


class TestStageResult:
    def test_defaults(self):
        r = StageResult(stage="test")
        assert r.row_count == 0
        assert r.extra == {}

    def test_with_extra(self):
        r = StageResult(stage="test", row_count=5, extra={"x": 1})
        assert r.extra["x"] == 1


# ---------------------------------------------------------------------------
# 6. Taxonomy alignment — assert ETL thresholds match taxonomy constants
# ---------------------------------------------------------------------------


class TestTaxonomyAlignment:
    """Assert that the ETL Python functions use the same constants as taxonomy.py."""

    def test_revoked_provider_points_match_taxonomy(self):
        """compute_seed_scores revoked flag must award REVOKED_PROVIDER.points."""
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=1,
            present_in_2025_enrollment_file=1,
            peer_case_count=0,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        assert risk == REVOKED_PROVIDER.points

    def test_not_enrolled_points_match_taxonomy(self):
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=0,
            peer_case_count=0,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        assert risk == NOT_IN_ENROLLMENT.points

    def test_enrolled_current_points_match_taxonomy(self):
        _, legit = compute_seed_scores(
            present_in_2026_revocation_file=1,  # to zero out no_revocation
            present_in_2025_enrollment_file=1,
            peer_case_count=0,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        assert legit == ENROLLED_CURRENT.points

    def test_no_revocation_points_match_taxonomy(self):
        _, legit = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=0,  # to zero out enrolled
            peer_case_count=0,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        assert legit == NO_REVOCATION.points

    def test_service_volume_top_tier_matches_taxonomy(self):
        top_tier = SERVICE_VOLUME_OUTLIER.z_tiers[0]
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=top_tier.z_min,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=0.0,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        assert risk == top_tier.points

    def test_charge_ratio_top_tier_matches_taxonomy(self):
        top_tier = CHARGE_RATIO_OUTLIER.z_tiers[0]
        risk, _ = compute_seed_scores(
            present_in_2026_revocation_file=0,
            present_in_2025_enrollment_file=1,
            peer_case_count=MIN_PEER_COUNT,
            service_volume_peer_z=0.0,
            services_per_bene_peer_z=0.0,
            submitted_to_allowed_peer_z=top_tier.z_min,
            payment_peer_z=0.0,
            medicare_participating_ind="N",
            provider_total_benes=0.0,
        )
        assert risk == top_tier.points

    def test_high_risk_threshold_matches_taxonomy(self):
        """High-risk label fires at exactly HIGH_RISK_SCORE_THRESHOLD."""
        risk = HIGH_RISK_SCORE_THRESHOLD
        legit = 0
        assert compute_seed_label(risk, legit) == "high_risk"

    def test_one_below_high_risk_threshold_is_not_high_risk(self):
        risk = HIGH_RISK_SCORE_THRESHOLD - 1
        legit = 0
        assert compute_seed_label(risk, legit) != "high_risk"
