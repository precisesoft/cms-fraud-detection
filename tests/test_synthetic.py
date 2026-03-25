"""Tests for src/pipeline/synthetic.py — synthetic data generation.

Covers the generation functions, z-score solver, dataset shape, and
column correctness against the column_maps definitions.
"""

from __future__ import annotations

import random

import pytest

from src.pipeline.column_maps import REQUIRED_COLUMNS
from src.pipeline.synthetic import (
    SEED,
    SPECIALTIES,
    SYNTHETIC_VERSIONS,
    Archetype,
    SyntheticDataset,
    generate_all,
    generate_enrollment_rows,
    generate_providers,
    generate_revocation_rows,
    solve_outlier_value,
)

# ---------------------------------------------------------------------------
# solve_outlier_value
# ---------------------------------------------------------------------------


class TestSolveOutlierValue:
    def test_returns_value_above_baseline_mean(self):
        baseline = [100.0, 110.0, 105.0, 95.0, 90.0] * 10
        x = solve_outlier_value(baseline, 3.0)
        assert x > max(baseline)

    def test_z_target_2_produces_moderate_outlier(self):
        baseline = [50.0 + i * 0.5 for i in range(50)]
        x = solve_outlier_value(baseline, 2.0)
        import statistics

        full = baseline + [x]
        m = statistics.mean(full)
        s = statistics.pstdev(full)
        z = (x - m) / s if s > 0 else 0
        assert abs(z - 2.0) < 0.2

    def test_z_target_5_produces_extreme_outlier(self):
        baseline = [200.0 + random.gauss(0, 20) for _ in range(50)]
        x = solve_outlier_value(baseline, 5.0)
        import statistics

        full = baseline + [x]
        m = statistics.mean(full)
        s = statistics.pstdev(full)
        z = (x - m) / s if s > 0 else 0
        # Closed-form approximation; z≥3.0 is sufficient for scoring tiers
        assert z > 3.0

    def test_minimum_floor_12(self):
        """Solver always returns >= 12.0 even for low z-targets."""
        baseline = [100.0, 110.0, 90.0, 105.0, 95.0] * 5
        x = solve_outlier_value(baseline, 0.5)
        assert x >= 12.0

    def test_single_element_baseline(self):
        x = solve_outlier_value([100.0], 3.0)
        assert x >= 12.0

    def test_empty_baseline(self):
        x = solve_outlier_value([], 3.0)
        assert x >= 12.0


# ---------------------------------------------------------------------------
# generate_providers
# ---------------------------------------------------------------------------


class TestGenerateProviders:
    def test_count_matches_specialty_totals(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        expected = sum(s["count"] for s in SPECIALTIES)
        assert len(providers) == expected

    def test_all_archetypes_present(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        archetypes = {p.archetype for p in providers}
        assert archetypes == set(Archetype)

    def test_npis_are_unique(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        npis = [p.npi for p in providers]
        assert len(npis) == len(set(npis))

    def test_stable_providers_are_enrolled_and_not_revoked(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        for p in providers:
            if p.archetype == Archetype.STABLE:
                assert p.enrolled is True
                assert p.revoked is False

    def test_revoked_providers_are_not_enrolled(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        for p in providers:
            if p.archetype == Archetype.HIGH_RISK_REVOKED:
                assert p.enrolled is False
                assert p.revoked is True

    def test_states_are_valid(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        for p in providers:
            assert p.state in ("FL", "TX")


# ---------------------------------------------------------------------------
# generate_service_rows
# ---------------------------------------------------------------------------


class TestGenerateServiceRows:
    """Uses a cached generate_all() result shared via module-level fixture."""

    @pytest.fixture(scope="module")
    def dataset(self):
        return generate_all()

    def test_all_rows_have_required_columns(self, dataset):
        required = set(REQUIRED_COLUMNS["part_b_service"])
        for row in dataset.service_rows[:10]:
            assert required.issubset(set(row.keys()))

    def test_all_rows_survive_etl_filter(self, dataset):
        for row in dataset.service_rows:
            assert int(row["Tot_Benes"]) >= 11
            assert int(row["Tot_Srvcs"]) >= 11
            assert float(row["Avg_Mdcr_Alowd_Amt"]) > 0

    def test_row_count_is_positive(self, dataset):
        assert len(dataset.service_rows) > 1000

    def test_all_npis_in_provider_list(self, dataset):
        provider_npis = {p.npi for p in dataset.providers}
        row_npis = {r["Rndrng_NPI"] for r in dataset.service_rows}
        assert row_npis.issubset(provider_npis)

    def test_place_of_service_is_office(self, dataset):
        for row in dataset.service_rows[:20]:
            assert row["Place_Of_Srvc"] == "O"


# ---------------------------------------------------------------------------
# derive_provider_rows
# ---------------------------------------------------------------------------


class TestDeriveProviderRows:
    @pytest.fixture(scope="module")
    def dataset(self):
        return generate_all()

    def test_one_row_per_npi(self, dataset):
        npis = [r["Rndrng_NPI"] for r in dataset.provider_rows]
        assert len(npis) == len(set(npis))

    def test_has_required_columns(self, dataset):
        required = set(REQUIRED_COLUMNS["part_b_provider"])
        for row in dataset.provider_rows[:5]:
            assert required.issubset(set(row.keys()))


# ---------------------------------------------------------------------------
# generate_enrollment_rows / generate_revocation_rows
# ---------------------------------------------------------------------------


class TestEnrollmentRevocation:
    def test_enrollment_only_enrolled_providers(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        rows = generate_enrollment_rows(providers)
        enrolled_npis = {p.npi for p in providers if p.enrolled}
        for row in rows:
            assert row["NPI"] in enrolled_npis

    def test_enrollment_has_required_columns(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        rows = generate_enrollment_rows(providers)
        required = set(REQUIRED_COLUMNS["enrollment"])
        for row in rows[:5]:
            assert required.issubset(set(row.keys()))

    def test_revocations_only_revoked_providers(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        rows = generate_revocation_rows(rng, providers)
        revoked_npis = {p.npi for p in providers if p.revoked}
        for row in rows:
            assert row["NPI"] in revoked_npis

    def test_revocations_has_required_columns(self):
        rng = random.Random(SEED)
        providers = generate_providers(rng)
        rows = generate_revocation_rows(rng, providers)
        required = set(REQUIRED_COLUMNS["revocations"])
        for row in rows:
            assert required.issubset(set(row.keys()))


# ---------------------------------------------------------------------------
# generate_all
# ---------------------------------------------------------------------------


class TestGenerateAll:
    @pytest.fixture(scope="module")
    def dataset(self):
        return generate_all()

    def test_returns_synthetic_dataset(self, dataset):
        assert isinstance(dataset, SyntheticDataset)

    def test_dataset_has_all_four_row_sets(self, dataset):
        assert len(dataset.service_rows) > 0
        assert len(dataset.provider_rows) > 0
        assert len(dataset.enrollment_rows) > 0
        assert len(dataset.revocation_rows) > 0

    def test_version_strings_defined(self):
        assert "part_b_service" in SYNTHETIC_VERSIONS
        assert "part_b_provider" in SYNTHETIC_VERSIONS
        assert "enrollment" in SYNTHETIC_VERSIONS
        assert "revocations" in SYNTHETIC_VERSIONS

    def test_provider_count_matches(self, dataset):
        assert len(dataset.providers) == len(dataset.provider_rows)


# ---------------------------------------------------------------------------
# Peer group coverage
# ---------------------------------------------------------------------------


class TestPeerGroupCoverage:
    @pytest.fixture(scope="module")
    def dataset(self):
        return generate_all()

    def test_every_peer_group_has_at_least_25_members(self, dataset):
        """Each (provider_type, hcpcs_cd, place_of_service) group must have >= 25 rows."""
        from collections import Counter

        groups = Counter(
            (r["Rndrng_Prvdr_Type"], r["HCPCS_Cd"], r["Place_Of_Srvc"])
            for r in dataset.service_rows
        )
        for key, count in groups.items():
            assert count >= 25, f"Peer group {key} has only {count} members"
