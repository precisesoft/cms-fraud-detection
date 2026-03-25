"""Unit tests for src/pipeline/column_maps.py."""

from __future__ import annotations

import pytest

from src.pipeline.column_maps import (
    COLUMN_MAPS,
    RAW_TABLE_NAMES,
    REQUIRED_COLUMNS,
)

VALID_SOURCE_TYPES = ["part_b_service", "part_b_provider", "enrollment", "revocations"]


# ---------------------------------------------------------------------------
# Structure / completeness
# ---------------------------------------------------------------------------


class TestColumnMapsStructure:
    def test_all_source_types_have_column_map(self) -> None:
        for src in VALID_SOURCE_TYPES:
            assert src in COLUMN_MAPS, f"Missing COLUMN_MAPS entry for {src!r}"

    def test_all_source_types_have_required_columns(self) -> None:
        for src in VALID_SOURCE_TYPES:
            assert src in REQUIRED_COLUMNS, f"Missing REQUIRED_COLUMNS entry for {src!r}"

    def test_all_source_types_have_raw_table_name(self) -> None:
        for src in VALID_SOURCE_TYPES:
            assert src in RAW_TABLE_NAMES, f"Missing RAW_TABLE_NAMES entry for {src!r}"

    def test_column_maps_keys_match_source_types(self) -> None:
        assert set(COLUMN_MAPS) == set(VALID_SOURCE_TYPES)

    def test_required_columns_keys_match_source_types(self) -> None:
        assert set(REQUIRED_COLUMNS) == set(VALID_SOURCE_TYPES)

    def test_raw_table_names_keys_match_source_types(self) -> None:
        assert set(RAW_TABLE_NAMES) == set(VALID_SOURCE_TYPES)


# ---------------------------------------------------------------------------
# Required columns are a subset of the column map
# ---------------------------------------------------------------------------


class TestRequiredColumnsSubset:
    def test_required_columns_are_subset_of_column_map(self) -> None:
        for src in VALID_SOURCE_TYPES:
            required = set(REQUIRED_COLUMNS[src])
            mapped = set(COLUMN_MAPS[src].keys())
            assert required.issubset(mapped), (
                f"Required columns not in column map for {src!r}: {required - mapped}"
            )


# ---------------------------------------------------------------------------
# part_b_service
# ---------------------------------------------------------------------------


class TestPartBServiceMap:
    def test_npi_column_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_service"]["Rndrng_NPI"] == "npi"

    def test_hcpcs_cd_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_service"]["HCPCS_Cd"] == "hcpcs_cd"

    def test_avg_submitted_charge_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_service"]["Avg_Sbmtd_Chrg"] == "avg_submitted_charge"

    def test_avg_medicare_allowed_amt_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_service"]["Avg_Mdcr_Alowd_Amt"] == "avg_medicare_allowed_amt"

    def test_avg_medicare_payment_amt_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_service"]["Avg_Mdcr_Pymt_Amt"] == "avg_medicare_payment_amt"

    def test_place_of_service_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_service"]["Place_Of_Srvc"] == "place_of_service"

    def test_required_columns_present(self) -> None:
        required = REQUIRED_COLUMNS["part_b_service"]
        assert "Rndrng_NPI" in required
        assert "HCPCS_Cd" in required
        assert "Tot_Benes" in required
        assert "Tot_Srvcs" in required

    def test_raw_table_name(self) -> None:
        assert RAW_TABLE_NAMES["part_b_service"] == "raw_part_b_service"

    def test_all_mapped_values_are_snake_case(self) -> None:
        for raw, renamed in COLUMN_MAPS["part_b_service"].items():
            assert renamed == renamed.lower(), f"{raw!r} maps to non-lower {renamed!r}"
            assert " " not in renamed, f"{raw!r} maps to value with space: {renamed!r}"


# ---------------------------------------------------------------------------
# part_b_provider
# ---------------------------------------------------------------------------


class TestPartBProviderMap:
    def test_npi_column_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_provider"]["Rndrng_NPI"] == "npi"

    def test_tot_hcpcs_cds_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_provider"]["Tot_HCPCS_Cds"] == "tot_hcpcs_cds"

    def test_tot_mdcr_pymt_amt_mapped(self) -> None:
        assert COLUMN_MAPS["part_b_provider"]["Tot_Mdcr_Pymt_Amt"] == "tot_medicare_payment_amt"

    def test_required_includes_npi_and_payment(self) -> None:
        required = REQUIRED_COLUMNS["part_b_provider"]
        assert "Rndrng_NPI" in required
        assert "Tot_Mdcr_Pymt_Amt" in required

    def test_raw_table_name(self) -> None:
        assert RAW_TABLE_NAMES["part_b_provider"] == "raw_part_b_provider"


# ---------------------------------------------------------------------------
# enrollment
# ---------------------------------------------------------------------------


class TestEnrollmentMap:
    def test_npi_column_mapped(self) -> None:
        assert COLUMN_MAPS["enrollment"]["NPI"] == "npi"

    def test_enrlmt_id_mapped(self) -> None:
        assert COLUMN_MAPS["enrollment"]["ENRLMT_ID"] == "enrlmt_id"

    def test_provider_type_desc_mapped(self) -> None:
        assert COLUMN_MAPS["enrollment"]["PROVIDER_TYPE_DESC"] == "provider_type_desc"

    def test_state_cd_mapped(self) -> None:
        assert COLUMN_MAPS["enrollment"]["STATE_CD"] == "state_cd"

    def test_required_includes_npi_enrlmt_state(self) -> None:
        required = REQUIRED_COLUMNS["enrollment"]
        assert "NPI" in required
        assert "ENRLMT_ID" in required
        assert "STATE_CD" in required

    def test_raw_table_name(self) -> None:
        assert RAW_TABLE_NAMES["enrollment"] == "raw_enrollment"


# ---------------------------------------------------------------------------
# revocations
# ---------------------------------------------------------------------------


class TestRevocationsMap:
    def test_npi_column_mapped(self) -> None:
        assert COLUMN_MAPS["revocations"]["NPI"] == "npi"

    def test_revocation_rsn_mapped(self) -> None:
        assert COLUMN_MAPS["revocations"]["REVOCATION_RSN"] == "revocation_rsn"

    def test_required_includes_npi_and_reason(self) -> None:
        required = REQUIRED_COLUMNS["revocations"]
        assert "NPI" in required
        assert "REVOCATION_RSN" in required

    def test_raw_table_name(self) -> None:
        assert RAW_TABLE_NAMES["revocations"] == "raw_revocations"


# ---------------------------------------------------------------------------
# No duplicate target names within a source type
# ---------------------------------------------------------------------------


class TestNoDuplicateTargetNames:
    @pytest.mark.parametrize("source_type", VALID_SOURCE_TYPES)
    def test_no_duplicate_target_column_names(self, source_type: str) -> None:
        targets = list(COLUMN_MAPS[source_type].values())
        assert len(targets) == len(set(targets)), (
            f"Duplicate target names in {source_type!r}: "
            f"{[t for t in targets if targets.count(t) > 1]}"
        )
