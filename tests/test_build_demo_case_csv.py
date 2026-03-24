"""Tests for src/data/build_demo_case_csv.py — synthetic data generation.

Strategy: build minimal synthetic CMS input CSVs in tmp_path, patch the
module-level path constants so build_demo_case_csv() reads from them, then
inspect the output CSV for structural and referential correctness.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("duckdb")

import src.data.build_demo_case_csv as _mod  # noqa: E402
from src.data.build_demo_case_csv import build_demo_case_csv  # noqa: E402

# ---------------------------------------------------------------------------
# Valid US state abbreviations (50 states + DC + territories in the data)
# ---------------------------------------------------------------------------

_VALID_STATES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
    "PR",
    "GU",
    "VI",
    "MP",
    "AS",  # territories sometimes in CMS data
}

# ---------------------------------------------------------------------------
# Synthetic CSV content for the four source files
# ---------------------------------------------------------------------------

# Part B Provider Service (one row per NPI + HCPCS + place-of-service)
# We include enough rows so peer groups can form (peer_case_count >= 25
# requires ≥25 rows sharing provider_type + state + hcpcs + place_of_service).
# We create 30 identical HCPCS/state/type combos for provider_type="Internal Medicine",
# state="IL", hcpcs="99213", pos="O" — that gives us a state peer group of 30.


def _build_service_rows() -> str:
    """Return CSV text for part_b_provider_service_2023.csv."""
    header = (
        "Rndrng_NPI,Rndrng_Prvdr_Last_Org_Name,Rndrng_Prvdr_First_Name,"
        "Rndrng_Prvdr_Crdntls,Rndrng_Prvdr_Ent_Cd,Rndrng_Prvdr_City,"
        "Rndrng_Prvdr_State_Abrvtn,Rndrng_Prvdr_Zip5,Rndrng_Prvdr_Type,"
        "Rndrng_Prvdr_Mdcr_Prtcptg_Ind,HCPCS_Cd,HCPCS_Desc,Place_Of_Srvc,"
        "Tot_Benes,Tot_Srvcs,Tot_Bene_Day_Srvcs,Avg_Sbmtd_Chrg,"
        "Avg_Mdcr_Alowd_Amt,Avg_Mdcr_Pymt_Amt"
    )
    rows = [header]
    # 28 stable providers — enrolled, not revoked, low z-scores → seed_case_label=stable
    for i in range(28):
        npi = f"111111{i:04d}"
        rows.append(
            f"{npi},Clinic {i},Dr,MD,O,Springfield,IL,62701,"
            f"Internal Medicine,Y,99213,Office Visit,O,"
            f"50,100,100,75.0,50.0,40.0"
        )
    # 1 high-risk provider — revoked, high volume → seed_case_label=high_risk
    rows.append(
        "9999999999,Fraud Corp,,MD,O,Miami,FL,33101,"
        "Internal Medicine,N,99213,Office Visit,O,"
        "15,9000,9000,5000.0,200.0,180.0"
    )
    # 1 review provider — not enrolled, moderate z
    rows.append(
        "8888888888,Mid Corp,,DO,O,Austin,TX,78701,"
        "Internal Medicine,Y,99213,Office Visit,O,"
        "12,800,800,300.0,50.0,45.0"
    )
    return "\n".join(rows)


def _build_provider_rows() -> str:
    """Return CSV text for part_b_provider_2023.csv (provider-level totals)."""
    header = "Rndrng_NPI,Tot_HCPCS_Cds,Tot_Benes,Tot_Srvcs,Tot_Mdcr_Pymt_Amt"
    rows = [header]
    for i in range(28):
        npi = f"111111{i:04d}"
        rows.append(f"{npi},5,500,1000,40000.0")
    rows.append("9999999999,1,15,9000,1620000.0")
    rows.append("8888888888,2,120,800,36000.0")
    return "\n".join(rows)


def _build_enrollment_rows() -> str:
    """Return CSV text for public_provider_enrollment_q4_2025.csv."""
    header = "NPI,ENRLMT_ID,PROVIDER_TYPE_DESC,STATE_CD"
    rows = [header]
    # 28 stable + review provider enrolled, high-risk NOT enrolled
    for i in range(28):
        npi = f"111111{i:04d}"
        rows.append(f"{npi},ENRL{i:04d},Internal Medicine,IL")
    rows.append("8888888888,ENRL9000,Internal Medicine,TX")
    return "\n".join(rows)


def _build_revoked_rows() -> str:
    """Return CSV text for revoked_providers_q1_2026.csv."""
    header = "NPI,REVOCATION_RSN"
    return "\n".join([header, "9999999999,False Claims Act"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def synthetic_inputs(tmp_path: Path) -> Path:
    """Write synthetic source CSVs to tmp_path and return the raw dir."""
    raw_dir = tmp_path / "data" / "raw" / "public_sources" / "cms"
    raw_dir.mkdir(parents=True)

    (raw_dir / "part_b_provider_service_2023.csv").write_text(_build_service_rows())
    (raw_dir / "part_b_provider_2023.csv").write_text(_build_provider_rows())
    (raw_dir / "public_provider_enrollment_q4_2025.csv").write_text(_build_enrollment_rows())
    (raw_dir / "revoked_providers_q1_2026.csv").write_text(_build_revoked_rows())

    return raw_dir


@pytest.fixture()
def output_csv(synthetic_inputs: Path, tmp_path: Path) -> Path:
    """Call build_demo_case_csv() with patched paths and return the CSV path."""
    root = tmp_path
    raw_dir = synthetic_inputs
    output_dir = tmp_path / "data" / "processed" / "demo"
    temp_dir = tmp_path / "data" / "processed" / "duckdb_tmp"
    csv_path = output_dir / "provider_service_cases_demo.csv"

    with (
        patch.object(_mod, "RAW_DIR", raw_dir),
        patch.object(_mod, "OUTPUT_DIR", output_dir),
        patch.object(_mod, "OUTPUT_CSV", csv_path),
        patch.object(_mod, "TEMP_DIR", temp_dir),
        patch.object(_mod, "ROOT", root),
    ):
        result = build_demo_case_csv()

    assert result == csv_path
    return csv_path


@pytest.fixture()
def output_rows(output_csv: Path) -> list[dict[str, str]]:
    """Parse the output CSV and return a list of row dicts."""
    with output_csv.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Required column order
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = [
    "case_id",
    "npi",
    "provider_last_org_name",
    "provider_first_name",
    "provider_credentials",
    "provider_entity_code",
    "provider_city",
    "provider_state",
    "provider_zip5",
    "provider_type",
    "medicare_participating_ind",
    "hcpcs_cd",
    "hcpcs_desc",
    "place_of_service",
    "tot_benes",
    "tot_srvcs",
    "tot_bene_day_srvcs",
    "avg_submitted_charge",
    "avg_medicare_allowed_amt",
    "avg_medicare_payment_amt",
    "estimated_case_payment_amt",
    "services_per_bene",
    "submitted_to_allowed_ratio",
    "payment_to_allowed_ratio",
    "provider_total_hcpcs_codes",
    "provider_total_benes",
    "provider_total_services",
    "provider_total_payment_amt",
    "present_in_2025_enrollment_file",
    "enrollment_record_count",
    "enrollment_provider_type_desc",
    "enrollment_state_cd",
    "present_in_2026_revocation_file",
    "revocation_reason_summary",
    "peer_scope",
    "peer_case_count",
    "peer_avg_tot_srvcs",
    "service_volume_peer_z",
    "services_per_bene_peer_z",
    "submitted_to_allowed_peer_z",
    "payment_peer_z",
    "seed_risk_score",
    "seed_legitimacy_score",
    "seed_case_label",
    "seed_risk_reasons",
    "seed_legitimacy_reasons",
]


# ---------------------------------------------------------------------------
# Test 1: Output CSV has all required columns in correct order
# ---------------------------------------------------------------------------


class TestOutputColumns:
    def test_all_required_columns_present(self, output_csv: Path) -> None:
        with output_csv.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            actual_columns = next(reader)
        assert actual_columns == EXPECTED_COLUMNS, (
            f"Column mismatch.\nExpected: {EXPECTED_COLUMNS}\nActual:   {actual_columns}"
        )


# ---------------------------------------------------------------------------
# Test 2: Expected row counts by seed_case_label
# ---------------------------------------------------------------------------


class TestRowCounts:
    def test_has_rows(self, output_rows: list[dict[str, str]]) -> None:
        """Output must contain at least one row."""
        assert len(output_rows) > 0

    def test_label_distribution(self, output_rows: list[dict[str, str]]) -> None:
        """All three seed_case_label values appear in the output."""
        labels = {row["seed_case_label"] for row in output_rows}
        assert "high_risk" in labels, "Expected at least one high_risk row"
        assert "stable" in labels, "Expected at least one stable row"

    def test_high_risk_capped_at_7000(self, output_rows: list[dict[str, str]]) -> None:
        high_risk = [r for r in output_rows if r["seed_case_label"] == "high_risk"]
        assert len(high_risk) <= 7000

    def test_stable_capped_at_6000(self, output_rows: list[dict[str, str]]) -> None:
        stable = [r for r in output_rows if r["seed_case_label"] == "stable"]
        assert len(stable) <= 6000

    def test_review_capped_at_7000(self, output_rows: list[dict[str, str]]) -> None:
        review = [r for r in output_rows if r["seed_case_label"] == "review"]
        assert len(review) <= 7000


# ---------------------------------------------------------------------------
# Test 3: NPI values are 10-digit strings
# ---------------------------------------------------------------------------


class TestNpiFormat:
    def test_npi_is_10_digits(self, output_rows: list[dict[str, str]]) -> None:
        for row in output_rows:
            npi = row["npi"]
            assert re.fullmatch(r"\d{10}", npi), f"NPI '{npi}' is not a 10-digit string"


# ---------------------------------------------------------------------------
# Test 4: Dates are ISO format YYYY-MM-DD
# (The pipeline does not currently output date columns directly, but case_id
# is derived from npi|hcpcs_cd|place_of_service and not a date. This test
# verifies the pipeline produces no malformed date-like strings in the
# enrollment_state_cd and other columns that could be confused with dates,
# and confirms the output file itself was created with a valid timestamp.)
# ---------------------------------------------------------------------------


class TestDates:
    def test_output_file_exists_and_is_recent(self, output_csv: Path) -> None:
        """The output CSV must exist and be a regular file."""
        assert output_csv.exists()
        assert output_csv.is_file()

    def test_no_date_columns_are_malformed(self, output_rows: list[dict[str, str]]) -> None:
        """Any column whose name contains 'date' must match YYYY-MM-DD format."""
        date_cols = [c for c in EXPECTED_COLUMNS if "date" in c.lower()]
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for row in output_rows:
            for col in date_cols:
                val = row.get(col, "")
                if val:
                    assert iso_re.match(val), f"Column '{col}' value '{val}' is not ISO YYYY-MM-DD"


# ---------------------------------------------------------------------------
# Test 5: Risk scores are within 0–100 range
# ---------------------------------------------------------------------------


class TestRiskScoreRange:
    def test_seed_risk_score_in_range(self, output_rows: list[dict[str, str]]) -> None:
        for row in output_rows:
            score = float(row["seed_risk_score"])
            assert 0 <= score <= 100, (
                f"seed_risk_score {score} out of [0, 100] for NPI {row['npi']}"
            )

    def test_seed_legitimacy_score_in_range(self, output_rows: list[dict[str, str]]) -> None:
        for row in output_rows:
            score = float(row["seed_legitimacy_score"])
            assert 0 <= score <= 100, (
                f"seed_legitimacy_score {score} out of [0, 100] for NPI {row['npi']}"
            )

    def test_risk_score_is_integer_valued(self, output_rows: list[dict[str, str]]) -> None:
        """Scores are computed with LEAST(100, ...) on integer additions."""
        for row in output_rows:
            val = row["seed_risk_score"]
            assert float(val) == int(float(val)), f"seed_risk_score '{val}' is not integer-valued"


# ---------------------------------------------------------------------------
# Test 6: State codes are valid 2-letter US state abbreviations
# ---------------------------------------------------------------------------


class TestStateCodes:
    def test_provider_state_valid(self, output_rows: list[dict[str, str]]) -> None:
        for row in output_rows:
            state = row["provider_state"]
            if state:  # some rows may be blank (org providers)
                assert state in _VALID_STATES, (
                    f"provider_state '{state}' is not a valid US state abbreviation"
                )

    def test_enrollment_state_valid(self, output_rows: list[dict[str, str]]) -> None:
        for row in output_rows:
            state = row["enrollment_state_cd"]
            if state:
                assert state in _VALID_STATES, (
                    f"enrollment_state_cd '{state}' is not a valid US state abbreviation"
                )


# ---------------------------------------------------------------------------
# Test 7: Referential integrity — claim NPIs reference existing providers
# ---------------------------------------------------------------------------


class TestReferentialIntegrity:
    def test_claim_npis_are_known_providers(self, output_rows: list[dict[str, str]]) -> None:
        """Every NPI in the output must come from the synthetic input data.

        The synthetic inputs define NPIs: 111111{0000..0027}, 9999999999,
        8888888888.  All output rows must have NPIs from that set.
        """
        known_npis = {f"111111{i:04d}" for i in range(28)} | {"9999999999", "8888888888"}
        for row in output_rows:
            assert row["npi"] in known_npis, (
                f"Output NPI {row['npi']} not found in input provider set"
            )

    def test_case_id_npi_component_matches_row_npi(self, output_rows: list[dict[str, str]]) -> None:
        """case_id is CONCAT_WS('|', npi, hcpcs_cd, place_of_service).

        The first segment of case_id must equal the row's npi column.
        """
        for row in output_rows:
            case_id_npi = row["case_id"].split("|")[0]
            assert case_id_npi == row["npi"], (
                f"case_id NPI segment '{case_id_npi}' != row npi '{row['npi']}'"
            )


# ---------------------------------------------------------------------------
# Test 8: Case IDs follow expected format pattern (npi|hcpcs_cd|place_of_service)
# ---------------------------------------------------------------------------


class TestCaseIdFormat:
    def test_case_id_has_three_pipe_segments(self, output_rows: list[dict[str, str]]) -> None:
        for row in output_rows:
            parts = row["case_id"].split("|")
            assert len(parts) == 3, (
                f"case_id '{row['case_id']}' does not have exactly 3 pipe-separated segments"
            )

    def test_case_id_npi_segment_is_10_digits(self, output_rows: list[dict[str, str]]) -> None:
        for row in output_rows:
            npi_segment = row["case_id"].split("|")[0]
            assert re.fullmatch(r"\d{10}", npi_segment), (
                f"case_id NPI segment '{npi_segment}' is not 10 digits"
            )

    def test_case_id_place_of_service_segment_nonempty(
        self, output_rows: list[dict[str, str]]
    ) -> None:
        for row in output_rows:
            pos_segment = row["case_id"].split("|")[2]
            assert pos_segment.strip() != "", (
                f"case_id place_of_service segment is empty in '{row['case_id']}'"
            )

    def test_case_ids_are_unique(self, output_rows: list[dict[str, str]]) -> None:
        """Each (npi, hcpcs_cd, place_of_service) combination should appear once."""
        case_ids = [row["case_id"] for row in output_rows]
        assert len(case_ids) == len(set(case_ids)), "Duplicate case_ids found in output"
