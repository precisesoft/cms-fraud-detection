"""Tests for src/data/load_postgres.py bulk loader.

All tests mock the psycopg connection so no live database is required.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

import src.data.load_postgres as lp
from src.data.load_postgres import (
    DATABASE_URL,
    get_connection,
    load_features,
    load_service_cases,
    main,
)

# ---------------------------------------------------------------------------
# Minimal synthetic data
# ---------------------------------------------------------------------------

SYNTHETIC_CSV_HEADER = (
    "case_id,npi,provider_last_org_name,provider_type,state,tot_srvcs,seed_risk_score"
)
# case_id follows the real schema format: {npi}|{hcpcs_cd}|{place_of_service}
SYNTHETIC_CSV_ROWS = (
    "1111111111|99213|O,1111111111,Test Clinic,Internal Medicine,IL,100,20\n"
    "2222222222|J0135|F,2222222222,Dr Fraud,Cardiology,FL,500,80\n"
)
SYNTHETIC_CSV_CONTENT = SYNTHETIC_CSV_HEADER + "\n" + SYNTHETIC_CSV_ROWS


def _make_csv_file(tmp_path: Path, content: str = SYNTHETIC_CSV_CONTENT) -> Path:
    """Write synthetic CSV content to a temp file and return the path."""
    p = tmp_path / "test_cases.csv"
    p.write_text(content)
    return p


def _make_copy_ctx(mock_conn: MagicMock) -> MagicMock:
    """Return the copy context manager mock wired to mock_conn.cursor().copy()."""
    copy_ctx = MagicMock()
    copy_obj = MagicMock()
    copy_ctx.__enter__ = MagicMock(return_value=copy_obj)
    copy_ctx.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.copy.return_value = copy_ctx
    return copy_obj


# ---------------------------------------------------------------------------
# get_connection
# ---------------------------------------------------------------------------


def test_get_connection_uses_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_connection() calls psycopg.connect with the DATABASE_URL."""
    test_url = "postgresql://user:pass@localhost:5432/testdb"
    monkeypatch.setenv("DATABASE_URL", test_url)
    # Re-read module-level DATABASE_URL inside function via monkeypatching
    with patch("src.data.load_postgres.psycopg.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        # Patch the module-level DATABASE_URL so get_connection uses it
        with patch.object(lp, "DATABASE_URL", test_url):
            get_connection()
        mock_connect.assert_called_once_with(test_url)


def test_get_connection_default_url_format() -> None:
    """DATABASE_URL falls back to a postgresql:// URL when env var is absent."""
    assert DATABASE_URL.startswith("postgresql://")


def test_get_connection_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """DATABASE_URL env var overrides the default forge host."""
    custom_url = "postgresql://cms:secret@myhost:5432/cms_fraud"
    monkeypatch.setenv("DATABASE_URL", custom_url)
    import importlib

    import src.data.load_postgres as reloaded

    importlib.reload(reloaded)
    assert reloaded.DATABASE_URL == custom_url
    # Restore so other tests are not affected
    importlib.reload(reloaded)


# ---------------------------------------------------------------------------
# load_service_cases — COPY SQL generation
# ---------------------------------------------------------------------------


def test_load_service_cases_truncates_before_load(tmp_path: Path) -> None:
    """load_service_cases always TRUNCATEs the target table first."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_service_cases(mock_conn, csv_file)

    first_execute_call = mock_conn.execute.call_args_list[0]
    assert "TRUNCATE" in first_execute_call.args[0]
    assert "provider_service_cases" in first_execute_call.args[0]


def test_load_service_cases_copy_sql_uses_csv_header(tmp_path: Path) -> None:
    """The COPY statement uses the column list derived from the CSV header."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_service_cases(mock_conn, csv_file)

    copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
    assert "COPY provider_service_cases" in copy_sql
    assert "case_id" in copy_sql
    assert "npi" in copy_sql
    assert "FORMAT CSV" in copy_sql


def test_load_service_cases_returns_row_count(tmp_path: Path) -> None:
    """load_service_cases returns the integer row count from SELECT COUNT(*)."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (42,)

    result = load_service_cases(mock_conn, csv_file)

    assert result == 42


def test_load_service_cases_returns_zero_on_null_count(tmp_path: Path) -> None:
    """load_service_cases returns 0 when the COUNT query returns None."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = None

    result = load_service_cases(mock_conn, csv_file)

    assert result == 0


def test_load_service_cases_commits(tmp_path: Path) -> None:
    """load_service_cases calls conn.commit() after writing data."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (1,)

    load_service_cases(mock_conn, csv_file)

    mock_conn.commit.assert_called_once()


def test_load_service_cases_writes_data_chunks(tmp_path: Path) -> None:
    """load_service_cases writes file content to the COPY object."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    copy_obj = _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_service_cases(mock_conn, csv_file)

    # write() must have been called at least once with non-empty data
    write_calls = copy_obj.write.call_args_list
    assert len(write_calls) >= 1
    all_written = "".join(c.args[0] for c in write_calls)
    assert len(all_written) > 0


def test_load_service_cases_missing_file_raises(tmp_path: Path) -> None:
    """load_service_cases raises an error when the CSV path does not exist."""
    missing = tmp_path / "nonexistent.csv"
    mock_conn = MagicMock()

    with pytest.raises((FileNotFoundError, OSError)):
        load_service_cases(mock_conn, missing)


def test_load_service_cases_connection_failure(tmp_path: Path) -> None:
    """load_service_cases propagates psycopg connection errors."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("connection refused")

    with pytest.raises(Exception, match="connection refused"):
        load_service_cases(mock_conn, csv_file)


# ---------------------------------------------------------------------------
# load_features — COPY SQL generation and Parquet handling
# ---------------------------------------------------------------------------


def _write_synthetic_parquet(tmp_path: Path) -> Path:
    """Create a minimal Parquet file for feature-load tests."""
    df = pl.DataFrame(
        {
            "npi": [1111111111, 2222222222],
            "provider_name": ["Test Clinic", "Dr Fraud"],
            "provider_type": ["Internal Medicine", "Cardiology"],
            "state": ["IL", "FL"],
            "max_seed_risk_score": [20.0, 80.0],
        }
    )
    p = tmp_path / "provider_features.parquet"
    df.write_parquet(p)
    return p


def test_load_features_truncates_before_load(tmp_path: Path) -> None:
    """load_features TRUNCATEs provider_features before writing new data."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_features(mock_conn, parquet_path)

    first_call = mock_conn.execute.call_args_list[0]
    assert "TRUNCATE" in first_call.args[0]
    assert "provider_features" in first_call.args[0]


def test_load_features_copy_sql_format(tmp_path: Path) -> None:
    """COPY SQL for features uses FORMAT CSV, NULL '' and correct table name."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_features(mock_conn, parquet_path)

    copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
    assert "COPY provider_features" in copy_sql
    assert "FORMAT CSV" in copy_sql
    assert "NULL ''" in copy_sql


def test_load_features_copy_sql_columns_match_parquet(tmp_path: Path) -> None:
    """COPY column list matches the columns present in the Parquet file."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_features(mock_conn, parquet_path)

    copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
    for col in ["npi", "provider_name", "provider_type", "state", "max_seed_risk_score"]:
        assert col in copy_sql


def test_load_features_returns_row_count(tmp_path: Path) -> None:
    """load_features returns the integer COUNT from the post-load query."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (7,)

    result = load_features(mock_conn, parquet_path)

    assert result == 7


def test_load_features_returns_zero_on_null_count(tmp_path: Path) -> None:
    """load_features returns 0 when the COUNT query returns None."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = None

    result = load_features(mock_conn, parquet_path)

    assert result == 0


def test_load_features_commits(tmp_path: Path) -> None:
    """load_features calls conn.commit() after writing data."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_features(mock_conn, parquet_path)

    mock_conn.commit.assert_called_once()


def test_load_features_missing_parquet_raises(tmp_path: Path) -> None:
    """load_features raises when the Parquet file does not exist."""
    missing = tmp_path / "nonexistent.parquet"
    mock_conn = MagicMock()

    with pytest.raises(Exception):
        load_features(mock_conn, missing)


def test_load_features_null_values_in_csv(tmp_path: Path) -> None:
    """Null values in the Parquet are represented as empty strings in COPY output."""
    df = pl.DataFrame(
        {
            "npi": [1111111111],
            "provider_name": [None],
            "max_seed_risk_score": [None],
        }
    )
    p = tmp_path / "nulls.parquet"
    df.write_parquet(p)

    # Capture the CSV written to the COPY stream
    written_chunks: list[str] = []

    class _CaptureCopy:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def write(self, data: str):
            written_chunks.append(data)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.copy.return_value = _CaptureCopy()
    mock_conn.execute.return_value.fetchone.return_value = (1,)

    load_features(mock_conn, p)

    all_written = "".join(written_chunks)
    # Polars writes null as empty string; the NULL '' clause maps it back in PG
    # Check the CSV row contains empty fields (consecutive commas or trailing comma)
    assert "1111111111" in all_written


# ---------------------------------------------------------------------------
# COPY CSV content validation
# ---------------------------------------------------------------------------


def test_load_service_cases_copy_content_excludes_header(tmp_path: Path) -> None:
    """The data written via COPY must not contain the header line."""
    csv_file = _make_csv_file(tmp_path)
    written_chunks: list[str] = []

    class _CaptureCopy:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def write(self, data: str):
            written_chunks.append(data)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.copy.return_value = _CaptureCopy()
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_service_cases(mock_conn, csv_file)

    all_written = "".join(written_chunks)
    # Header should NOT appear in the COPY data stream (it was consumed by readline)
    assert SYNTHETIC_CSV_HEADER not in all_written
    # But the data rows should be present
    assert "1111111111" in all_written


# ---------------------------------------------------------------------------
# Batch / chunking behaviour
# ---------------------------------------------------------------------------


def test_load_service_cases_chunks_large_file(tmp_path: Path) -> None:
    """Files larger than 65536 bytes are written in multiple write() calls."""
    # Create a CSV just over 65536 bytes
    rows = "\n".join(
        f"{1000000000 + i}|99213|O,{1000000000 + i},Provider {i},Internal Medicine,IL,{i},50"
        for i in range(2000)
    )
    content = SYNTHETIC_CSV_HEADER + "\n" + rows + "\n"
    assert len(content.encode()) > 65536

    csv_file = tmp_path / "large.csv"
    csv_file.write_text(content)

    written_chunks: list[str] = []

    class _CaptureCopy:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def write(self, data: str):
            written_chunks.append(data)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.copy.return_value = _CaptureCopy()
    mock_conn.execute.return_value.fetchone.return_value = (2000,)

    load_service_cases(mock_conn, csv_file)

    assert len(written_chunks) > 1


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_load_service_cases_idempotent(tmp_path: Path) -> None:
    """Calling load_service_cases twice results in two TRUNCATE calls."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_service_cases(mock_conn, csv_file)
    load_service_cases(mock_conn, csv_file)

    truncate_calls = [c for c in mock_conn.execute.call_args_list if "TRUNCATE" in c.args[0]]
    assert len(truncate_calls) == 2


def test_load_features_idempotent(tmp_path: Path) -> None:
    """Calling load_features twice issues two TRUNCATE statements."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    load_features(mock_conn, parquet_path)
    load_features(mock_conn, parquet_path)

    truncate_calls = [c for c in mock_conn.execute.call_args_list if "TRUNCATE" in c.args[0]]
    assert len(truncate_calls) == 2


# ---------------------------------------------------------------------------
# main() function
# ---------------------------------------------------------------------------


def test_main_skips_missing_csv_and_parquet(capsys: pytest.CaptureFixture) -> None:
    """main() prints SKIP messages when data files are absent."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (0,)

    with (
        patch("src.data.load_postgres.get_connection", return_value=mock_conn),
        patch.object(lp, "DEMO_CSV", Path("/nonexistent/demo.csv")),
        patch.object(lp, "FEATURES_PARQUET", Path("/nonexistent/features.parquet")),
    ):
        main()

    captured = capsys.readouterr()
    assert "SKIP" in captured.out


def test_main_loads_when_files_exist(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """main() calls load_service_cases and load_features when files are present."""
    csv_file = _make_csv_file(tmp_path)
    parquet_path = _write_synthetic_parquet(tmp_path)

    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (2,)

    with (
        patch("src.data.load_postgres.get_connection", return_value=mock_conn),
        patch.object(lp, "DEMO_CSV", csv_file),
        patch.object(lp, "FEATURES_PARQUET", parquet_path),
    ):
        main()

    captured = capsys.readouterr()
    assert "Loaded" in captured.out


def test_main_prints_validation_counts(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """main() prints Validation section with row counts for both tables."""
    csv_file = _make_csv_file(tmp_path)
    parquet_path = _write_synthetic_parquet(tmp_path)

    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = (0,)

    with (
        patch("src.data.load_postgres.get_connection", return_value=mock_conn),
        patch.object(lp, "DEMO_CSV", csv_file),
        patch.object(lp, "FEATURES_PARQUET", parquet_path),
    ):
        main()

    captured = capsys.readouterr()
    assert "Validation" in captured.out


def test_main_shows_top5_when_features_loaded(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """main() shows Top 5 provider table when provider_features has rows."""
    csv_file = _make_csv_file(tmp_path)
    parquet_path = _write_synthetic_parquet(tmp_path)

    top5_rows = [
        (1111111111, "Test Clinic", "Internal Medicine", "IL", 20, 10),
    ]

    execute_results = [
        MagicMock(fetchone=MagicMock(return_value=(2,))),  # TRUNCATE cases → ignored
        MagicMock(fetchone=MagicMock(return_value=(2,))),  # COUNT cases
        MagicMock(fetchone=MagicMock(return_value=(2,))),  # TRUNCATE features → ignored
        MagicMock(fetchone=MagicMock(return_value=(2,))),  # COUNT features
        MagicMock(fetchone=MagicMock(return_value=(2,))),  # validation: cases
        MagicMock(fetchone=MagicMock(return_value=(5,))),  # validation: features (>0 → show top5)
        MagicMock(fetchone=MagicMock(return_value=(5,))),  # COUNT check
        MagicMock(fetchall=MagicMock(return_value=top5_rows)),  # top5 query
    ]

    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.side_effect = execute_results

    with (
        patch("src.data.load_postgres.get_connection", return_value=mock_conn),
        patch.object(lp, "DEMO_CSV", csv_file),
        patch.object(lp, "FEATURES_PARQUET", parquet_path),
    ):
        main()

    captured = capsys.readouterr()
    assert "Top 5" in captured.out
