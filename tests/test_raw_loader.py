"""Tests for src/pipeline/raw_loader.py.

All tests use small in-memory fixture CSVs.  No live database connection is
required — psycopg is fully mocked.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.pipeline.raw_loader import (
    LoadResult,
    ValidationResult,
    _compute_file_hash,
    _safe_identifier,
    load_raw_csv,
    validate_csv,
)

# ---------------------------------------------------------------------------
# Fixture CSV content — one per source type
# ---------------------------------------------------------------------------

PART_B_SERVICE_CSV = (
    "Rndrng_NPI,Rndrng_Prvdr_Last_Org_Name,Rndrng_Prvdr_Type,"
    "HCPCS_Cd,HCPCS_Desc,Place_Of_Srvc,"
    "Tot_Benes,Tot_Srvcs,Tot_Bene_Day_Srvcs,"
    "Avg_Sbmtd_Chrg,Avg_Mdcr_Alowd_Amt,Avg_Mdcr_Pymt_Amt\n"
    "1234567890,Smith John,Internal Medicine,99213,Office visit,O,20,40,40,150.00,80.00,64.00\n"
    "9876543210,Fraud Clinic,Cardiology,J0135,Inj adalimumab,F,15,200,200,1200.00,900.00,720.00\n"
)

PART_B_PROVIDER_CSV = (
    "Rndrng_NPI,Rndrng_Prvdr_Last_Org_Name,Rndrng_Prvdr_Type,"
    "Tot_HCPCS_Cds,Tot_Benes,Tot_Srvcs,Tot_Sbmtd_Chrg,"
    "Tot_Mdcr_Alowd_Amt,Tot_Mdcr_Pymt_Amt\n"
    "1234567890,Smith John,Internal Medicine,5,120,240,18000.00,9600.00,7680.00\n"
    "9876543210,Fraud Clinic,Cardiology,2,15,200,240000.00,180000.00,144000.00\n"
)

ENROLLMENT_CSV = (
    "NPI,ENRLMT_ID,PROVIDER_TYPE_CODE,PROVIDER_TYPE_DESC,STATE_CD,"
    "ENRLMT_STUS_EFCTV_DT,ENRLMT_END_DT,MDCR_STUS_CD\n"
    "1234567890,I20240101001,14,INTERNAL MEDICINE,IL,01/01/2024,,A\n"
    "9876543210,I20230601002,06,CARDIOLOGY,FL,06/01/2023,,A\n"
)

REVOCATIONS_CSV = "NPI,REVOCATION_RSN\n9876543210,Fraudulent billing scheme\n"

# Source type → CSV content map
_FIXTURE_CSV: dict[str, str] = {
    "part_b_service": PART_B_SERVICE_CSV,
    "part_b_provider": PART_B_PROVIDER_CSV,
    "enrollment": ENROLLMENT_CSV,
    "revocations": REVOCATIONS_CSV,
}


def _write_csv(tmp_path: Path, source_type: str, content: str | None = None) -> Path:
    p = tmp_path / f"{source_type}.csv"
    p.write_text(content if content is not None else _FIXTURE_CSV[source_type])
    return p


def _make_copy_ctx(mock_conn: MagicMock) -> MagicMock:
    """Wire up a COPY context-manager mock on *mock_conn*."""
    copy_obj = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=copy_obj)
    ctx.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.copy.return_value = ctx
    return copy_obj


class _CaptureCopy:
    """Context-manager that captures data written to a COPY stream."""

    def __init__(self) -> None:
        self.chunks: list[str] = []

    def __enter__(self) -> _CaptureCopy:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def write(self, data: str) -> None:
        self.chunks.append(data)

    @property
    def all_written(self) -> str:
        return "".join(self.chunks)


# ---------------------------------------------------------------------------
# _compute_file_hash
# ---------------------------------------------------------------------------


class TestComputeFileHash:
    def test_returns_sha256_hex_string(self, tmp_path: Path) -> None:
        p = tmp_path / "data.csv"
        p.write_bytes(b"hello,world\n1,2\n")
        result = _compute_file_hash(p)
        expected = hashlib.sha256(b"hello,world\n1,2\n").hexdigest()
        assert result == expected

    def test_different_content_produces_different_hash(self, tmp_path: Path) -> None:
        p1 = tmp_path / "a.csv"
        p2 = tmp_path / "b.csv"
        p1.write_text("col\nval1\n")
        p2.write_text("col\nval2\n")
        assert _compute_file_hash(p1) != _compute_file_hash(p2)

    def test_same_content_produces_same_hash(self, tmp_path: Path) -> None:
        content = "npi,code\n1234,99213\n"
        p1 = tmp_path / "c1.csv"
        p2 = tmp_path / "c2.csv"
        p1.write_text(content)
        p2.write_text(content)
        assert _compute_file_hash(p1) == _compute_file_hash(p2)


# ---------------------------------------------------------------------------
# validate_csv — happy-path
# ---------------------------------------------------------------------------


class TestValidateCsvHappyPath:
    @pytest.mark.parametrize("source_type", list(_FIXTURE_CSV))
    def test_valid_csv_returns_valid_true(self, tmp_path: Path, source_type: str) -> None:
        p = _write_csv(tmp_path, source_type)
        result = validate_csv(p, source_type)
        assert result.valid is True

    @pytest.mark.parametrize("source_type", list(_FIXTURE_CSV))
    def test_valid_csv_has_no_missing_required(self, tmp_path: Path, source_type: str) -> None:
        p = _write_csv(tmp_path, source_type)
        result = validate_csv(p, source_type)
        assert result.missing_required == []

    def test_returns_validation_result_type(self, tmp_path: Path) -> None:
        p = _write_csv(tmp_path, "revocations")
        assert isinstance(validate_csv(p, "revocations"), ValidationResult)


# ---------------------------------------------------------------------------
# validate_csv — extra columns
# ---------------------------------------------------------------------------


class TestValidateCsvExtraColumns:
    def test_extra_columns_are_reported(self, tmp_path: Path) -> None:
        csv_content = "NPI,REVOCATION_RSN,EXTRA_COL\n1234567890,Fraud,SomeValue\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        result = validate_csv(p, "revocations")
        assert "EXTRA_COL" in result.extra_columns

    def test_extra_columns_still_valid(self, tmp_path: Path) -> None:
        csv_content = "NPI,REVOCATION_RSN,EXTRA_COL\n1234567890,Fraud,SomeValue\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        result = validate_csv(p, "revocations")
        assert result.valid is True

    def test_extra_columns_produce_warning(self, tmp_path: Path) -> None:
        csv_content = "NPI,REVOCATION_RSN,EXTRA_COL\n1234567890,Fraud,SomeValue\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        result = validate_csv(p, "revocations")
        assert len(result.warnings) > 0
        assert any("EXTRA_COL" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# validate_csv — missing required columns
# ---------------------------------------------------------------------------


class TestValidateCsvMissingRequired:
    def test_missing_required_column_returns_invalid(self, tmp_path: Path) -> None:
        # REVOCATION_RSN is required for revocations
        csv_content = "NPI\n1234567890\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        result = validate_csv(p, "revocations")
        assert result.valid is False

    def test_missing_required_listed_in_missing_required(self, tmp_path: Path) -> None:
        csv_content = "NPI\n1234567890\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        result = validate_csv(p, "revocations")
        assert "REVOCATION_RSN" in result.missing_required

    def test_multiple_missing_required_columns(self, tmp_path: Path) -> None:
        csv_content = "Rndrng_NPI\n1234567890\n"
        p = _write_csv(tmp_path, "part_b_service", csv_content)
        result = validate_csv(p, "part_b_service")
        assert result.valid is False
        assert len(result.missing_required) > 1


# ---------------------------------------------------------------------------
# validate_csv — unknown source type
# ---------------------------------------------------------------------------


class TestValidateCsvUnknownSourceType:
    def test_unknown_source_type_raises_value_error(self, tmp_path: Path) -> None:
        p = tmp_path / "x.csv"
        p.write_text("col\nval\n")
        with pytest.raises(ValueError, match="Unknown source_type"):
            validate_csv(p, "invalid_source")


# ---------------------------------------------------------------------------
# load_raw_csv — happy-path (all four source types)
# ---------------------------------------------------------------------------


class TestLoadRawCsvHappyPath:
    @pytest.mark.parametrize("source_type", list(_FIXTURE_CSV))
    def test_returns_load_result(
        self, tmp_path: Path, source_type: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, source_type)
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        mock_conn.execute.return_value = MagicMock()
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        result = load_raw_csv(p, source_type, "2023", mock_conn, "admin")
        assert isinstance(result, LoadResult)

    @pytest.mark.parametrize("source_type", list(_FIXTURE_CSV))
    def test_row_count_matches_csv(
        self, tmp_path: Path, source_type: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, source_type)
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        result = load_raw_csv(p, source_type, "2023", mock_conn, "admin")
        # Both fixture CSVs have 2 data rows (revocations has 1)
        expected_rows = 1 if source_type == "revocations" else 2
        assert result.row_count == expected_rows

    @pytest.mark.parametrize("source_type", list(_FIXTURE_CSV))
    def test_file_hash_is_sha256(
        self, tmp_path: Path, source_type: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, source_type)
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        result = load_raw_csv(p, source_type, "2023", mock_conn, "admin")
        # SHA-256 hex digest is 64 characters
        assert len(result.file_hash) == 64
        assert all(c in "0123456789abcdef" for c in result.file_hash)

    @pytest.mark.parametrize("source_type", list(_FIXTURE_CSV))
    def test_file_hash_matches_expected(
        self, tmp_path: Path, source_type: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, source_type)
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        result = load_raw_csv(p, source_type, "2023", mock_conn, "admin")
        expected = _compute_file_hash(p)
        assert result.file_hash == expected


# ---------------------------------------------------------------------------
# load_raw_csv — DB interactions
# ---------------------------------------------------------------------------


class TestLoadRawCsvDbInteractions:
    def test_deletes_existing_version_before_load(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        delete_calls = [c for c in mock_conn.execute.call_args_list if "DELETE" in str(c)]
        assert len(delete_calls) == 1

    def test_delete_uses_correct_table_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        delete_sql = str(mock_conn.execute.call_args_list[0])
        assert "raw_revocations" in delete_sql

    def test_delete_passes_version_as_parameter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        first_execute_args = mock_conn.execute.call_args_list[0].args
        assert "q1_2026" in first_execute_args[1]

    def test_copy_uses_correct_table_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
        assert "raw_revocations" in copy_sql

    def test_copy_sql_includes_source_version_column(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
        assert "source_version" in copy_sql

    def test_upserts_data_source_versions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        upsert_calls = [
            c for c in mock_conn.execute.call_args_list if "data_source_versions" in str(c)
        ]
        assert len(upsert_calls) == 1

    def test_upsert_passes_correct_params(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "analyst")
        upsert_call = next(
            c for c in mock_conn.execute.call_args_list if "data_source_versions" in str(c)
        )
        params = upsert_call.args[1]
        assert params[0] == "revocations"
        assert params[1] == "q1_2026"
        assert params[4] == "analyst"

    def test_calls_commit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        mock_conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# load_raw_csv — column renaming
# ---------------------------------------------------------------------------


class TestLoadRawCsvColumnRenaming:
    def test_part_b_service_columns_renamed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """COPY column list uses renamed (internal) names, not raw CMS names."""
        p = _write_csv(tmp_path, "part_b_service")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "part_b_service", "2023", mock_conn, "admin")
        copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
        # Internal names should appear
        assert "npi" in copy_sql
        assert "hcpcs_cd" in copy_sql
        assert "avg_submitted_charge" in copy_sql
        # Raw CMS names must NOT appear
        assert "Rndrng_NPI" not in copy_sql
        assert "HCPCS_Cd" not in copy_sql
        assert "Avg_Sbmtd_Chrg" not in copy_sql

    def test_enrollment_columns_renamed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "enrollment")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "enrollment", "q4_2025", mock_conn, "admin")
        copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
        assert "npi" in copy_sql
        assert "enrlmt_id" in copy_sql
        assert "state_cd" in copy_sql
        assert "NPI" not in copy_sql
        assert "ENRLMT_ID" not in copy_sql


# ---------------------------------------------------------------------------
# load_raw_csv — extra columns are silently dropped
# ---------------------------------------------------------------------------


class TestLoadRawCsvExtraColumns:
    def test_extra_columns_dropped_not_copied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        csv_content = "NPI,REVOCATION_RSN,EXTRA_UNKNOWN_COL\n1234567890,Fraud,SomeValue\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        result = load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
        assert "EXTRA_UNKNOWN_COL" not in copy_sql
        # The warning is recorded in result
        assert any("EXTRA_UNKNOWN_COL" in w for w in result.validation_warnings)


# ---------------------------------------------------------------------------
# load_raw_csv — invalid / missing columns raise ValueError
# ---------------------------------------------------------------------------


class TestLoadRawCsvMissingRequired:
    def test_missing_required_raises_value_error(self, tmp_path: Path) -> None:
        csv_content = "NPI\n1234567890\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        mock_conn = MagicMock()
        with pytest.raises(ValueError, match="missing required columns"):
            load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")

    def test_error_message_lists_missing_columns(self, tmp_path: Path) -> None:
        csv_content = "NPI\n1234567890\n"
        p = _write_csv(tmp_path, "revocations", csv_content)
        mock_conn = MagicMock()
        with pytest.raises(ValueError, match="REVOCATION_RSN"):
            load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")

    def test_unknown_source_type_raises_value_error(self, tmp_path: Path) -> None:
        p = tmp_path / "x.csv"
        p.write_text("col\nval\n")
        mock_conn = MagicMock()
        with pytest.raises(ValueError, match="Unknown source_type"):
            load_raw_csv(p, "bad_type", "2023", mock_conn, "admin")


# ---------------------------------------------------------------------------
# load_raw_csv — file archiving
# ---------------------------------------------------------------------------


class TestLoadRawCsvArchiving:
    def test_original_file_is_archived(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        archive_root = tmp_path / "archive"
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", archive_root)
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        archived = archive_root / "revocations" / "q1_2026" / p.name
        assert archived.exists()

    def test_archived_content_matches_original(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        original_content = p.read_text()
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        archive_root = tmp_path / "archive"
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", archive_root)
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        archived = archive_root / "revocations" / "q1_2026" / p.name
        assert archived.read_text() == original_content

    def test_archive_directory_created_if_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        archive_root = tmp_path / "does_not_exist" / "archive"
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", archive_root)
        load_raw_csv(p, "revocations", "v1", mock_conn, "admin")
        assert (archive_root / "revocations" / "v1").is_dir()


# ---------------------------------------------------------------------------
# load_raw_csv — idempotency (reload same version)
# ---------------------------------------------------------------------------


class TestLoadRawCsvIdempotency:
    def test_reload_issues_delete_each_time(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "revocations")
        mock_conn = MagicMock()
        _make_copy_ctx(mock_conn)
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        load_raw_csv(p, "revocations", "q1_2026", mock_conn, "admin")
        delete_calls = [c for c in mock_conn.execute.call_args_list if "DELETE" in str(c)]
        assert len(delete_calls) == 2


# ---------------------------------------------------------------------------
# Integration-style test: load → verify data written to COPY stream
# ---------------------------------------------------------------------------


class TestLoadRawCsvIntegration:
    def test_part_b_service_data_written_to_copy_stream(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end: CSV is read, columns renamed, metadata added, streamed."""
        p = _write_csv(tmp_path, "part_b_service")
        capture = _CaptureCopy()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.copy.return_value = capture
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        result = load_raw_csv(p, "part_b_service", "2023", mock_conn, "admin")

        assert "1234567890" in capture.all_written  # NPI appears
        assert "2023" in capture.all_written  # source_version appears
        assert result.row_count == 2

    def test_enrollment_data_written_to_copy_stream(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        p = _write_csv(tmp_path, "enrollment")
        capture = _CaptureCopy()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.copy.return_value = capture
        monkeypatch.setattr("src.pipeline.raw_loader.ARCHIVE_DIR", tmp_path / "archive")
        result = load_raw_csv(p, "enrollment", "q4_2025", mock_conn, "admin")

        assert "1234567890" in capture.all_written
        assert "q4_2025" in capture.all_written
        assert result.row_count == 2


# ---------------------------------------------------------------------------
# _safe_identifier
# ---------------------------------------------------------------------------


class TestSafeIdentifier:
    def test_valid_lowercase_name_passes(self) -> None:
        assert _safe_identifier("npi") == "npi"

    def test_valid_snake_case_passes(self) -> None:
        assert _safe_identifier("avg_submitted_charge") == "avg_submitted_charge"

    def test_valid_table_name_passes(self) -> None:
        assert _safe_identifier("raw_part_b_service") == "raw_part_b_service"

    def test_uppercase_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("NPI")

    def test_mixed_case_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("Rndrng_NPI")

    def test_hyphen_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("bad-name")

    def test_semicolon_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("name; DROP TABLE users--")

    def test_space_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("bad name")

    def test_leading_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("1bad")
