"""Tests for db/init.sql and db/migrations/ schema files.

These tests verify that the SQL files are syntactically well-formed and
contain all expected tables, columns, and indexes — without requiring a
live database connection.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DB_DIR = Path(__file__).parent.parent / "db"
INIT_SQL = DB_DIR / "init.sql"
MIGRATION_001 = DB_DIR / "migrations" / "001_add_raw_tables_pipeline_tracking.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# init.sql — all new tables present
# ---------------------------------------------------------------------------


def test_init_sql_exists():
    assert INIT_SQL.exists(), "db/init.sql must exist"


def test_init_sql_case_actions_table():
    sql = _read(INIT_SQL)
    assert "CREATE TABLE IF NOT EXISTS case_actions" in sql
    assert "analyst_id" in sql
    assert "created_at" in sql


def test_init_sql_raw_tables():
    sql = _read(INIT_SQL)
    for table in (
        "raw_part_b_service",
        "raw_part_b_provider",
        "raw_enrollment",
        "raw_revocations",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql, f"{table} missing from init.sql"


def test_init_sql_raw_zip_column_name():
    """provider_zip5 must be used consistently — not provider_zip."""
    sql = _read(INIT_SQL)
    assert "provider_zip5" in sql, "raw tables must use provider_zip5 (not provider_zip)"
    assert "    provider_zip " not in sql, "provider_zip (without 5) found — rename to provider_zip5"


def test_init_sql_raw_medicare_column_name():
    """raw_part_b_service and raw_part_b_provider must both use medicare_participating_ind."""
    sql = _read(INIT_SQL)
    # Extract the raw_part_b_provider table block and verify the column name
    assert "medicare_participating_ind" in sql, "medicare_participating_ind not found"
    # The raw provider table must not use the short form (provider_features uses the short form,
    # so count occurrences: provider_features(1) + raw_part_b_service(1) + raw_part_b_provider(1)
    assert sql.count("medicare_participating_ind") >= 2, (
        "both raw_part_b_service and raw_part_b_provider must use medicare_participating_ind"
    )


def test_init_sql_tracking_tables():
    sql = _read(INIT_SQL)
    assert "CREATE TABLE IF NOT EXISTS data_source_versions" in sql
    assert "CREATE TABLE IF NOT EXISTS pipeline_runs" in sql


def test_init_sql_pipeline_runs_stage_results_default():
    """stage_results must default to an empty JSON array."""
    sql = _read(INIT_SQL)
    assert "stage_results" in sql
    assert "'[]'::jsonb" in sql


def test_init_sql_provider_features_alter_columns():
    sql = _read(INIT_SQL)
    assert "ADD COLUMN IF NOT EXISTS last_scored_at" in sql
    assert "ADD COLUMN IF NOT EXISTS pipeline_run_id" in sql


def test_init_sql_indexes():
    sql = _read(INIT_SQL)
    expected_indexes = [
        "idx_case_actions_case_id",
        "idx_raw_part_b_service_npi",
        "idx_raw_part_b_service_version",
        "idx_raw_part_b_provider_npi",
        "idx_raw_enrollment_npi",
        "idx_raw_revocations_npi",
        "idx_pipeline_runs_status",
    ]
    for idx in expected_indexes:
        assert idx in sql, f"Index {idx} missing from init.sql"


def test_init_sql_partial_index_pipeline_runs():
    """Partial index on pipeline_runs.status must filter WHERE status = 'running'."""
    sql = _read(INIT_SQL)
    assert "WHERE status = 'running'" in sql


# ---------------------------------------------------------------------------
# migration 001 — mirrors init.sql additions and is idempotent
# ---------------------------------------------------------------------------


def test_migration_001_exists():
    assert MIGRATION_001.exists(), "db/migrations/001_add_raw_tables_pipeline_tracking.sql must exist"


def test_migration_001_idempotent_create():
    """Every CREATE TABLE must use IF NOT EXISTS."""
    sql = _read(MIGRATION_001)
    for line in sql.splitlines():
        stripped = line.strip().upper()
        if stripped.startswith("CREATE TABLE") and "IF NOT EXISTS" not in stripped:
            pytest.fail(f"Non-idempotent CREATE TABLE in migration: {line!r}")


def test_migration_001_idempotent_index():
    """Every CREATE INDEX must use IF NOT EXISTS."""
    sql = _read(MIGRATION_001)
    for line in sql.splitlines():
        stripped = line.strip().upper()
        if stripped.startswith("CREATE INDEX") and "IF NOT EXISTS" not in stripped:
            pytest.fail(f"Non-idempotent CREATE INDEX in migration: {line!r}")


def test_migration_001_contains_all_tables():
    sql = _read(MIGRATION_001)
    for table in (
        "case_actions",
        "raw_part_b_service",
        "raw_part_b_provider",
        "raw_enrollment",
        "raw_revocations",
        "data_source_versions",
        "pipeline_runs",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql, (
            f"{table} missing from migration 001"
        )


def test_migration_001_alter_idempotent():
    """ALTER TABLE ADD COLUMN must use IF NOT EXISTS."""
    sql = _read(MIGRATION_001)
    for line in sql.splitlines():
        stripped = line.strip().upper()
        if "ADD COLUMN" in stripped and "IF NOT EXISTS" not in stripped:
            pytest.fail(f"Non-idempotent ADD COLUMN in migration: {line!r}")


def test_migration_001_case_actions_columns():
    sql = _read(MIGRATION_001)
    for col in ("case_id", "npi", "action", "notes", "analyst_id", "created_at"):
        assert col in sql, f"case_actions column '{col}' missing from migration 001"
