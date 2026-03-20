"""Tests for text-to-SQL engine — validation and formatting."""

from __future__ import annotations

import pytest

from src.ai.text_to_sql import SQLValidationError, _format_answer, _format_value, validate_sql

# ---------------------------------------------------------------------------
# SQL validation tests
# ---------------------------------------------------------------------------


def test_validate_basic_select():
    assert validate_sql("SELECT 1") == "SELECT 1 LIMIT 500"


def test_validate_with_existing_limit():
    sql = "SELECT * FROM provider_features LIMIT 10"
    assert validate_sql(sql) == "SELECT * FROM provider_features LIMIT 10"


def test_validate_with_cte():
    sql = "WITH x AS (SELECT 1) SELECT * FROM x"
    result = validate_sql(sql)
    assert result.startswith("WITH x AS")
    assert "LIMIT 500" in result


def test_validate_strips_semicolons():
    sql = "SELECT count(*) FROM provider_features;;;"
    result = validate_sql(sql)
    assert not result.endswith(";")


def test_validate_strips_markdown_fences():
    """validate_sql doesn't strip fences (text_to_sql does), but rejects if not SELECT."""
    with pytest.raises(SQLValidationError, match="must start with SELECT"):
        validate_sql("```sql\nSELECT 1\n```")


def test_reject_empty():
    with pytest.raises(SQLValidationError, match="Empty"):
        validate_sql("")


def test_reject_unanswerable():
    with pytest.raises(SQLValidationError, match="UNANSWERABLE"):
        validate_sql("UNANSWERABLE")


@pytest.mark.parametrize(
    "bad_sql",
    [
        "INSERT INTO provider_features VALUES ('x')",
        "UPDATE provider_features SET state='XX'",
        "DELETE FROM provider_features",
        "DROP TABLE provider_features",
        "ALTER TABLE provider_features ADD COLUMN x TEXT",
        "CREATE TABLE evil (id INT)",
        "TRUNCATE provider_features",
        "GRANT ALL ON provider_features TO public",
    ],
)
def test_reject_mutations(bad_sql: str):
    with pytest.raises(SQLValidationError, match="Forbidden keyword|must start with SELECT"):
        validate_sql(bad_sql)


def test_reject_non_select_start():
    with pytest.raises(SQLValidationError, match="must start with SELECT"):
        validate_sql("EXPLAIN SELECT 1")


# ---------------------------------------------------------------------------
# Advanced injection prevention tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_sql",
    [
        "SELECT 1 UNION SELECT username FROM pg_user",
        "SELECT * FROM provider_features UNION ALL SELECT 1,2,3",
    ],
)
def test_reject_union(bad_sql: str):
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql(bad_sql)


@pytest.mark.parametrize(
    "bad_sql",
    [
        "SELECT pg_sleep(10)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT lo_import('/etc/passwd')",
        "SELECT * FROM dblink('host=evil', 'SELECT 1')",
    ],
)
def test_reject_server_functions(bad_sql: str):
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql(bad_sql)


def test_reject_sql_line_comment():
    with pytest.raises(SQLValidationError, match="comments are not allowed"):
        validate_sql("SELECT 1 -- DROP TABLE provider_features")


def test_reject_sql_block_comment():
    with pytest.raises(SQLValidationError, match="comments are not allowed"):
        validate_sql("SELECT /* DROP TABLE */ 1 FROM provider_features")


def test_reject_multi_statement():
    with pytest.raises(SQLValidationError, match="Multiple statements"):
        validate_sql("SELECT 1; DROP TABLE provider_features")


def test_reject_privilege_escalation():
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT set role admin")


def test_valid_select_still_passes():
    """Ensure hardening doesn't break legitimate queries."""
    result = validate_sql("SELECT npi, provider_name FROM provider_features WHERE state = 'FL'")
    assert result.startswith("SELECT npi")
    assert "LIMIT 500" in result


def test_valid_cte_with_aggregation():
    sql = (
        "WITH risk AS (SELECT state, count(*) AS n FROM provider_features "
        "WHERE max_seed_risk_score > 50 GROUP BY state) "
        "SELECT * FROM risk ORDER BY n DESC LIMIT 10"
    )
    assert validate_sql(sql) == sql


# ---------------------------------------------------------------------------
# Format tests
# ---------------------------------------------------------------------------


def test_format_value_none():
    assert _format_value(None) == "N/A"


def test_format_value_large_float():
    assert _format_value(1234567.89) == "1,234,568"


def test_format_value_small_float():
    assert _format_value(3.14159) == "3.14"


def test_format_value_string():
    assert _format_value("hello") == "hello"


def test_format_answer_no_results():
    assert "No results" in _format_answer("q", [], [])


def test_format_answer_scalar():
    result = _format_answer("q", ["count"], [{"count": 42}])
    assert "42" in result


def test_format_answer_single_row():
    result = _format_answer("q", ["name", "state"], [{"name": "Smith", "state": "FL"}])
    assert "Smith" in result
    assert "FL" in result


def test_format_answer_multiple_rows():
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    result = _format_answer("q", ["id"], rows)
    assert "3 results" in result
