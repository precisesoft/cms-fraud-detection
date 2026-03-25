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
    UpsertResult,
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


def _make_service_cases_execute_seq(
    staging_count: int = 2,
    returning_rows: list[tuple[bool]] | None = None,
) -> list[MagicMock]:
    """Build the ordered list of execute() return values for load_service_cases."""
    if returning_rows is None:
        returning_rows = [(True,)] * staging_count  # all inserts by default
    return [
        MagicMock(),  # CREATE TEMP TABLE
        MagicMock(fetchone=MagicMock(return_value=(staging_count,))),  # COUNT staging
        MagicMock(fetchall=MagicMock(return_value=returning_rows)),  # INSERT RETURNING
    ]


def _make_features_execute_seq(
    staging_count: int = 2,
    returning_rows: list[tuple[bool]] | None = None,
) -> list[MagicMock]:
    """Build the ordered list of execute() return values for load_features."""
    if returning_rows is None:
        returning_rows = [(True,)] * staging_count
    return [
        MagicMock(),  # CREATE TEMP TABLE
        MagicMock(fetchone=MagicMock(return_value=(staging_count,))),  # COUNT staging
        MagicMock(fetchall=MagicMock(return_value=returning_rows)),  # INSERT RETURNING
    ]


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
# UpsertResult
# ---------------------------------------------------------------------------


def test_upsert_result_total() -> None:
    """UpsertResult.total sums all three delta counts."""
    r = UpsertResult(rows_inserted=3, rows_updated=2, rows_unchanged=5)
    assert r.total == 10


def test_upsert_result_all_zero() -> None:
    """UpsertResult.total is 0 when all counts are zero."""
    r = UpsertResult(rows_inserted=0, rows_updated=0, rows_unchanged=0)
    assert r.total == 0


# ---------------------------------------------------------------------------
# load_service_cases — staging table and upsert SQL
# ---------------------------------------------------------------------------


def test_load_service_cases_uses_staging_table(tmp_path: Path) -> None:
    """load_service_cases creates a staging temp table, not TRUNCATE."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq()
    _make_copy_ctx(mock_conn)

    load_service_cases(mock_conn, csv_file)

    execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
    assert any("CREATE TEMP TABLE" in s for s in execute_sqls)
    assert not any("TRUNCATE" in s for s in execute_sqls)


def test_load_service_cases_upsert_sql_uses_on_conflict(tmp_path: Path) -> None:
    """The INSERT statement targets the staging table and uses ON CONFLICT."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq()
    _make_copy_ctx(mock_conn)

    load_service_cases(mock_conn, csv_file)

    execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
    upsert_sql = next(s for s in execute_sqls if "ON CONFLICT" in s)
    assert "provider_service_cases" in upsert_sql
    assert "ON CONFLICT (case_id) DO UPDATE" in upsert_sql
    assert "RETURNING" in upsert_sql


def test_load_service_cases_copy_targets_staging(tmp_path: Path) -> None:
    """COPY writes into the staging table, not directly into provider_service_cases."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq()
    _make_copy_ctx(mock_conn)

    load_service_cases(mock_conn, csv_file)

    copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
    assert "_load_staging_service_cases" in copy_sql
    assert "FORMAT CSV" in copy_sql


def test_load_service_cases_copy_sql_uses_csv_header(tmp_path: Path) -> None:
    """The COPY statement includes column names derived from the CSV header."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq()
    _make_copy_ctx(mock_conn)

    load_service_cases(mock_conn, csv_file)

    copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
    assert "case_id" in copy_sql
    assert "npi" in copy_sql


def test_load_service_cases_returns_upsert_result(tmp_path: Path) -> None:
    """load_service_cases returns an UpsertResult (not a plain int)."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq(
        staging_count=2, returning_rows=[(True,), (True,)]
    )
    _make_copy_ctx(mock_conn)

    result = load_service_cases(mock_conn, csv_file)

    assert type(result).__name__ == "UpsertResult"
    assert hasattr(result, "rows_inserted")
    assert hasattr(result, "rows_updated")
    assert hasattr(result, "rows_unchanged")


def test_load_service_cases_all_inserts(tmp_path: Path) -> None:
    """All-new rows → rows_inserted equals staging count, updated/unchanged = 0."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq(
        staging_count=2, returning_rows=[(True,), (True,)]
    )
    _make_copy_ctx(mock_conn)

    result = load_service_cases(mock_conn, csv_file)

    assert result.rows_inserted == 2
    assert result.rows_updated == 0
    assert result.rows_unchanged == 0
    assert result.total == 2


def test_load_service_cases_all_updates(tmp_path: Path) -> None:
    """Existing rows with changed data → rows_updated equals staging count."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq(
        staging_count=2, returning_rows=[(False,), (False,)]
    )
    _make_copy_ctx(mock_conn)

    result = load_service_cases(mock_conn, csv_file)

    assert result.rows_inserted == 0
    assert result.rows_updated == 2
    assert result.rows_unchanged == 0


def test_load_service_cases_all_unchanged(tmp_path: Path) -> None:
    """Existing rows with identical data → rows_unchanged equals staging count."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    # Staging has 2 rows but RETURNING is empty (WHERE clause skipped updates)
    mock_conn.execute.side_effect = _make_service_cases_execute_seq(
        staging_count=2, returning_rows=[]
    )
    _make_copy_ctx(mock_conn)

    result = load_service_cases(mock_conn, csv_file)

    assert result.rows_inserted == 0
    assert result.rows_updated == 0
    assert result.rows_unchanged == 2


def test_load_service_cases_mixed_delta(tmp_path: Path) -> None:
    """Mix of insert/update/unchanged is accounted for correctly."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    # 3 staging rows: 1 insert (True) + 1 update (False) + 1 unchanged (not returned)
    mock_conn.execute.side_effect = _make_service_cases_execute_seq(
        staging_count=3, returning_rows=[(True,), (False,)]
    )
    _make_copy_ctx(mock_conn)

    result = load_service_cases(mock_conn, csv_file)

    assert result.rows_inserted == 1
    assert result.rows_updated == 1
    assert result.rows_unchanged == 1
    assert result.total == 3


def test_load_service_cases_commits(tmp_path: Path) -> None:
    """load_service_cases calls conn.commit() after writing data."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq()
    _make_copy_ctx(mock_conn)

    load_service_cases(mock_conn, csv_file)

    mock_conn.commit.assert_called_once()


def test_load_service_cases_writes_data_chunks(tmp_path: Path) -> None:
    """load_service_cases writes file content to the COPY object."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_service_cases_execute_seq()
    copy_obj = _make_copy_ctx(mock_conn)

    load_service_cases(mock_conn, csv_file)

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
# load_features — staging table and upsert SQL
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


def test_load_features_uses_staging_table(tmp_path: Path) -> None:
    """load_features creates a staging temp table, not TRUNCATE."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq()
    _make_copy_ctx(mock_conn)

    load_features(mock_conn, parquet_path)

    execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
    assert any("CREATE TEMP TABLE" in s for s in execute_sqls)
    assert not any("TRUNCATE" in s for s in execute_sqls)


def test_load_features_upsert_sql_uses_on_conflict(tmp_path: Path) -> None:
    """The INSERT statement uses ON CONFLICT (npi) DO UPDATE."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq()
    _make_copy_ctx(mock_conn)

    load_features(mock_conn, parquet_path)

    execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
    upsert_sql = next(s for s in execute_sqls if "ON CONFLICT" in s)
    assert "provider_features" in upsert_sql
    assert "ON CONFLICT (npi) DO UPDATE" in upsert_sql
    assert "RETURNING" in upsert_sql


def test_load_features_copy_targets_staging(tmp_path: Path) -> None:
    """COPY writes into the staging table, not directly into provider_features."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq()
    _make_copy_ctx(mock_conn)

    load_features(mock_conn, parquet_path)

    copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
    assert "_load_staging_features" in copy_sql
    assert "FORMAT CSV" in copy_sql
    assert "NULL ''" in copy_sql


def test_load_features_copy_sql_columns_match_parquet(tmp_path: Path) -> None:
    """COPY column list matches the columns present in the Parquet file."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq()
    _make_copy_ctx(mock_conn)

    load_features(mock_conn, parquet_path)

    copy_sql = mock_conn.cursor.return_value.copy.call_args.args[0]
    for col in ["npi", "provider_name", "provider_type", "state", "max_seed_risk_score"]:
        assert col in copy_sql


def test_load_features_returns_upsert_result(tmp_path: Path) -> None:
    """load_features returns an UpsertResult."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq()
    _make_copy_ctx(mock_conn)

    result = load_features(mock_conn, parquet_path)

    assert type(result).__name__ == "UpsertResult"
    assert hasattr(result, "rows_inserted")
    assert hasattr(result, "rows_updated")
    assert hasattr(result, "rows_unchanged")


def test_load_features_all_inserts(tmp_path: Path) -> None:
    """All-new NPIs → rows_inserted equals staging count."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq(
        staging_count=2, returning_rows=[(True,), (True,)]
    )
    _make_copy_ctx(mock_conn)

    result = load_features(mock_conn, parquet_path)

    assert result.rows_inserted == 2
    assert result.rows_updated == 0
    assert result.rows_unchanged == 0


def test_load_features_all_updates(tmp_path: Path) -> None:
    """Existing NPIs with changed data → rows_updated equals staging count."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq(
        staging_count=2, returning_rows=[(False,), (False,)]
    )
    _make_copy_ctx(mock_conn)

    result = load_features(mock_conn, parquet_path)

    assert result.rows_inserted == 0
    assert result.rows_updated == 2
    assert result.rows_unchanged == 0


def test_load_features_all_unchanged(tmp_path: Path) -> None:
    """Existing NPIs with identical data → rows_unchanged equals staging count."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq(staging_count=2, returning_rows=[])
    _make_copy_ctx(mock_conn)

    result = load_features(mock_conn, parquet_path)

    assert result.rows_inserted == 0
    assert result.rows_updated == 0
    assert result.rows_unchanged == 2


def test_load_features_mixed_delta(tmp_path: Path) -> None:
    """Mix of insert/update/unchanged is counted correctly."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq(
        staging_count=3, returning_rows=[(True,), (False,)]
    )
    _make_copy_ctx(mock_conn)

    result = load_features(mock_conn, parquet_path)

    assert result.rows_inserted == 1
    assert result.rows_updated == 1
    assert result.rows_unchanged == 1
    assert result.total == 3


def test_load_features_commits(tmp_path: Path) -> None:
    """load_features calls conn.commit() after writing data."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = _make_features_execute_seq()
    _make_copy_ctx(mock_conn)

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
    mock_conn.execute.side_effect = _make_features_execute_seq(staging_count=1)

    load_features(mock_conn, p)

    all_written = "".join(written_chunks)
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
    mock_conn.execute.side_effect = _make_service_cases_execute_seq()

    load_service_cases(mock_conn, csv_file)

    all_written = "".join(written_chunks)
    assert SYNTHETIC_CSV_HEADER not in all_written
    assert "1111111111" in all_written


# ---------------------------------------------------------------------------
# Batch / chunking behaviour
# ---------------------------------------------------------------------------


def test_load_service_cases_chunks_large_file(tmp_path: Path) -> None:
    """Files larger than 65536 bytes are written in multiple write() calls."""
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
    mock_conn.execute.side_effect = _make_service_cases_execute_seq(
        staging_count=2000, returning_rows=[(True,)] * 2000
    )

    load_service_cases(mock_conn, csv_file)

    assert len(written_chunks) > 1


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_load_service_cases_idempotent(tmp_path: Path) -> None:
    """Calling load_service_cases twice produces the same result (no TRUNCATE)."""
    csv_file = _make_csv_file(tmp_path)
    mock_conn = MagicMock()
    # Provide execute results for two sequential calls (6 execute calls total)
    mock_conn.execute.side_effect = _make_service_cases_execute_seq(
        staging_count=2, returning_rows=[(True,), (True,)]
    ) + _make_service_cases_execute_seq(staging_count=2, returning_rows=[(False,), (False,)])
    _make_copy_ctx(mock_conn)

    result1 = load_service_cases(mock_conn, csv_file)
    result2 = load_service_cases(mock_conn, csv_file)

    # First call: all inserts; second call: all updates (same data → could be unchanged)
    assert result1.rows_inserted == 2
    assert result2.rows_updated == 2
    execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
    assert not any("TRUNCATE" in s for s in execute_sqls)


def test_load_features_idempotent(tmp_path: Path) -> None:
    """Calling load_features twice produces consistent results (no TRUNCATE)."""
    parquet_path = _write_synthetic_parquet(tmp_path)
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = (
        _make_features_execute_seq(staging_count=2, returning_rows=[(True,), (True,)])
        + _make_features_execute_seq(staging_count=2, returning_rows=[])  # second: unchanged
    )
    _make_copy_ctx(mock_conn)

    result1 = load_features(mock_conn, parquet_path)
    result2 = load_features(mock_conn, parquet_path)

    assert result1.rows_inserted == 2
    assert result2.rows_unchanged == 2
    execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
    assert not any("TRUNCATE" in s for s in execute_sqls)


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
    mock_conn.execute.side_effect = (
        _make_service_cases_execute_seq(staging_count=2, returning_rows=[(True,), (True,)])
        + _make_features_execute_seq(staging_count=2, returning_rows=[(True,), (True,)])
        + [
            MagicMock(fetchone=MagicMock(return_value=(2,))),  # validation: cases
            MagicMock(fetchone=MagicMock(return_value=(0,))),  # validation: features
            MagicMock(fetchone=MagicMock(return_value=(0,))),  # top5 check
        ]
    )

    with (
        patch("src.data.load_postgres.get_connection", return_value=mock_conn),
        patch.object(lp, "DEMO_CSV", csv_file),
        patch.object(lp, "FEATURES_PARQUET", parquet_path),
    ):
        main()

    captured = capsys.readouterr()
    assert "inserted=" in captured.out


def test_main_prints_validation_counts(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """main() prints Validation section with row counts for both tables."""
    csv_file = _make_csv_file(tmp_path)
    parquet_path = _write_synthetic_parquet(tmp_path)

    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.side_effect = (
        _make_service_cases_execute_seq(staging_count=2, returning_rows=[])
        + _make_features_execute_seq(staging_count=2, returning_rows=[])
        + [
            MagicMock(fetchone=MagicMock(return_value=(0,))),  # validation: cases
            MagicMock(fetchone=MagicMock(return_value=(0,))),  # validation: features
            MagicMock(fetchone=MagicMock(return_value=(0,))),  # top5 check
        ]
    )

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

    mock_conn = MagicMock()
    _make_copy_ctx(mock_conn)
    mock_conn.execute.side_effect = (
        _make_service_cases_execute_seq(staging_count=2, returning_rows=[(True,), (True,)])
        + _make_features_execute_seq(staging_count=2, returning_rows=[(True,), (True,)])
        + [
            MagicMock(fetchone=MagicMock(return_value=(2,))),  # validation: cases
            MagicMock(fetchone=MagicMock(return_value=(5,))),  # validation: features >0 → top5
            MagicMock(fetchone=MagicMock(return_value=(5,))),  # COUNT check before top5
            MagicMock(fetchall=MagicMock(return_value=top5_rows)),  # top5 query
        ]
    )

    with (
        patch("src.data.load_postgres.get_connection", return_value=mock_conn),
        patch.object(lp, "DEMO_CSV", csv_file),
        patch.object(lp, "FEATURES_PARQUET", parquet_path),
    ):
        main()

    captured = capsys.readouterr()
    assert "Top 5" in captured.out
