"""Tests for text-to-SQL engine — validation and formatting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.text_to_sql import (
    SQLValidationError,
    _format_answer,
    _format_value,
    _synthesize_results,
    validate_sql,
)

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
# Edge-case injection tests (extra credit)
# ---------------------------------------------------------------------------


def test_reject_union_case_insensitive():
    """UNION in mixed case should still be caught."""
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT 1 UnIoN SELECT 2")


def test_reject_tab_separated_union():
    """UNION preceded by tab instead of space."""
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT 1\tUNION\tSELECT 2")


def test_reject_newline_separated_multi_statement():
    """Newline between statements should still be blocked."""
    with pytest.raises(SQLValidationError, match="Multiple statements"):
        validate_sql("SELECT 1;\nDROP TABLE provider_features")


def test_reject_pg_read_binary_file():
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT pg_read_binary_file('/etc/shadow')")


def test_reject_lo_export():
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT lo_export(12345, '/tmp/data')")


def test_reject_dblink_exec():
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT dblink_exec('host=evil', 'DROP TABLE x')")


def test_reject_set_session():
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT set session authorization 'admin'")


def test_reject_copy():
    with pytest.raises(SQLValidationError, match="Forbidden keyword|must start with SELECT"):
        validate_sql("COPY provider_features TO '/tmp/dump.csv'")


def test_valid_where_clause_with_union_substring():
    """Column name containing 'union' substring should NOT be blocked (word boundary)."""
    result = validate_sql("SELECT reunion_date FROM events LIMIT 10")
    assert "reunion_date" in result


def test_valid_select_with_subquery():
    sql = (
        "SELECT npi, (SELECT count(*) FROM provider_service_cases c "
        "WHERE c.npi = p.npi) AS case_count "
        "FROM provider_features p LIMIT 10"
    )
    assert validate_sql(sql) == sql


def test_valid_case_expression():
    """CASE WHEN should not be confused with forbidden keywords."""
    sql = (
        "SELECT npi, CASE WHEN max_seed_risk_score >= 51 THEN 'high' "
        "ELSE 'low' END AS band FROM provider_features LIMIT 10"
    )
    assert validate_sql(sql) == sql


def test_valid_string_literal_with_union_word():
    """'Credit Union Bank' in a WHERE clause should NOT be blocked."""
    sql = "SELECT npi FROM provider_features WHERE provider_name = 'Credit Union Bank' LIMIT 10"
    assert validate_sql(sql) == sql


def test_valid_string_literal_with_delete_word():
    """String literal containing DELETE keyword should pass."""
    sql = "SELECT npi FROM provider_features WHERE notes = 'delete this record' LIMIT 10"
    assert validate_sql(sql) == sql


def test_reject_union_outside_string_literal():
    """UNION keyword outside a string literal must still be blocked."""
    with pytest.raises(SQLValidationError, match="Forbidden keyword"):
        validate_sql("SELECT npi FROM provider_features WHERE name = 'safe' UNION SELECT 1")


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


# ---------------------------------------------------------------------------
# Synthesis tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesize_results_returns_summary():
    mock_resp = {"text": "Internal Medicine leads with 23% flagging rate."}
    with patch(
        "src.ai.text_to_sql.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        result = await _synthesize_results(
            "Which specialties have the most outliers?",
            ["specialty", "count"],
            [
                {"specialty": "Internal Medicine", "count": 42},
                {"specialty": "Cardiology", "count": 31},
            ],
        )
    assert result is not None
    assert "Internal Medicine" in result


@pytest.mark.asyncio
async def test_synthesize_results_fallback_on_error():
    with patch(
        "src.ai.text_to_sql.invoke",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        result = await _synthesize_results(
            "test question",
            ["col"],
            [{"col": 1}, {"col": 2}],
        )
    assert result is None


@pytest.mark.asyncio
async def test_synthesize_limits_to_10_rows():
    rows = [{"id": i} for i in range(20)]
    mock_resp = {"text": "Summary of 20 rows."}
    with patch(
        "src.ai.text_to_sql.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock:
        await _synthesize_results("q", ["id"], rows)
        call_args = mock.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "20 total rows" in user_msg


# ---------------------------------------------------------------------------
# text_to_sql() end-to-end tests (lines 105-161)
# ---------------------------------------------------------------------------


def _make_async_cursor(columns: list[str], rows: list[tuple]):
    """Build a mock async cursor that returns canned description + rows."""
    cur = AsyncMock()
    cur.description = [MagicMock(name=col) for col in columns]
    for desc_mock, col_name in zip(cur.description, columns):
        desc_mock.name = col_name
    cur.fetchall = AsyncMock(return_value=rows)
    cur.execute = AsyncMock()

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=cur)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_async_conn(columns: list[str], rows: list[tuple]):
    """Build a mock AsyncConnection whose cursor() returns canned data."""
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=_make_async_cursor(columns, rows))
    return conn


@pytest.mark.asyncio
async def test_text_to_sql_basic_select():
    """Basic SELECT returning a single scalar row."""
    from src.ai.text_to_sql import text_to_sql

    conn = _make_async_conn(["count"], [(42,)])

    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch(
            "src.ai.text_to_sql.invoke",
            new_callable=AsyncMock,
            return_value={"text": "SELECT count(*) FROM providers"},
        ),
    ):
        result = await text_to_sql("How many providers?", conn)

    assert result["sql"].startswith("SELECT count(*)")
    assert result["row_count"] == 1
    assert result["columns"] == ["count"]
    assert result["rows"] == [{"count": 42}]
    assert "42" in result["answer"]


@pytest.mark.asyncio
async def test_text_to_sql_markdown_fences_stripped():
    """SQL wrapped in ```sql ... ``` fences should be cleaned before validation."""
    from src.ai.text_to_sql import text_to_sql

    conn = _make_async_conn(["npi"], [("1234567890",)])

    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch(
            "src.ai.text_to_sql.invoke",
            new_callable=AsyncMock,
            return_value={"text": "```sql\nSELECT npi FROM provider_features LIMIT 1\n```"},
        ),
    ):
        result = await text_to_sql("Give me an NPI", conn)

    assert result["sql"].startswith("SELECT npi")
    assert "```" not in result["sql"]


@pytest.mark.asyncio
async def test_text_to_sql_multi_row_triggers_synthesis():
    """Multi-row results should invoke _synthesize_results and use its output."""
    from src.ai.text_to_sql import text_to_sql

    rows = [("FL", 42), ("TX", 35), ("CA", 28)]
    conn = _make_async_conn(["state", "count"], rows)

    synthesis_text = "Florida leads with 42 high-risk providers."
    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch(
            "src.ai.text_to_sql.invoke",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "text": (
                        "SELECT state, count(*) FROM provider_features GROUP BY state LIMIT 500"
                    )
                },
                {"text": synthesis_text},
            ],
        ),
    ):
        result = await text_to_sql("States with most high-risk providers?", conn)

    assert result["row_count"] == 3
    assert result["answer"] == synthesis_text


@pytest.mark.asyncio
async def test_text_to_sql_unanswerable_raises():
    """When the LLM returns UNANSWERABLE, text_to_sql should propagate SQLValidationError."""
    from src.ai.text_to_sql import text_to_sql

    conn = _make_async_conn([], [])

    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch(
            "src.ai.text_to_sql.invoke",
            new_callable=AsyncMock,
            return_value={"text": "UNANSWERABLE"},
        ),
        pytest.raises(SQLValidationError, match="UNANSWERABLE"),
    ):
        await text_to_sql("What is the patient's diagnosis?", conn)


@pytest.mark.asyncio
async def test_text_to_sql_with_history():
    """Conversation history should be prepended to messages."""
    from src.ai.text_to_sql import text_to_sql

    conn = _make_async_conn(["total"], [(100,)])
    history = [
        {"role": "user", "content": "prior question"},
        {"role": "assistant", "content": "prior answer"},
    ]

    captured_messages: list[dict] = []

    async def capture_invoke(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return {"text": "SELECT count(*) FROM provider_features LIMIT 500"}

    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch("src.ai.text_to_sql.invoke", side_effect=capture_invoke),
    ):
        await text_to_sql("Follow-up question", conn, history=history)

    # history items appear before the new user message
    assert len(captured_messages) >= 3
    assert captured_messages[0]["content"] == "prior question"
    assert captured_messages[-1]["content"] == "Follow-up question"


@pytest.mark.asyncio
async def test_text_to_sql_single_row_multi_col():
    """Single row with multiple columns should list col: value pairs in the answer."""
    from src.ai.text_to_sql import text_to_sql

    conn = _make_async_conn(["npi", "state"], [("1234567890", "FL")])

    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch(
            "src.ai.text_to_sql.invoke",
            new_callable=AsyncMock,
            return_value={"text": "SELECT npi, state FROM provider_features LIMIT 1"},
        ),
    ):
        result = await text_to_sql("Get one provider", conn)

    assert "npi" in result["answer"]
    assert "1234567890" in result["answer"]
    assert "FL" in result["answer"]


@pytest.mark.asyncio
async def test_text_to_sql_no_rows_returns_no_results():
    """Zero rows from DB should return a 'No results' answer."""
    from src.ai.text_to_sql import text_to_sql

    conn = _make_async_conn(["npi"], [])

    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch(
            "src.ai.text_to_sql.invoke",
            new_callable=AsyncMock,
            return_value={"text": "SELECT npi FROM provider_features WHERE state = 'ZZ' LIMIT 500"},
        ),
    ):
        result = await text_to_sql("Providers in ZZ?", conn)

    assert result["row_count"] == 0
    assert "No results" in result["answer"]


@pytest.mark.asyncio
async def test_text_to_sql_synthesis_none_keeps_format_answer():
    """When _synthesize_results returns None the formatted answer is kept."""
    from src.ai.text_to_sql import text_to_sql

    rows = [("FL", 10), ("TX", 8)]
    conn = _make_async_conn(["state", "cnt"], rows)

    with (
        patch("src.ai.text_to_sql.build_text_to_sql_system_prompt", return_value="sys"),
        patch(
            "src.ai.text_to_sql.invoke",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "text": "SELECT state, count(*) AS cnt"
                    " FROM provider_features GROUP BY state LIMIT 500"
                },
                RuntimeError("synthesis failed"),
            ],
        ),
    ):
        result = await text_to_sql("State counts", conn)

    # synthesis raised → fell back to _format_answer which says "Found N results."
    assert result["row_count"] == 2
    assert "2" in result["answer"] or "results" in result["answer"].lower()


# ---------------------------------------------------------------------------
# _format_answer additional branch coverage (lines 171-188)
# ---------------------------------------------------------------------------


def test_format_answer_multi_row_count():
    """Multiple rows returns a 'Found N results.' message."""
    rows = [{"id": i} for i in range(5)]
    result = _format_answer("q", ["id"], rows)
    assert "5" in result


def test_format_answer_single_col_scalar_none():
    """Scalar result of None formats as N/A."""
    result = _format_answer("q", ["val"], [{"val": None}])
    assert result == "N/A"


def test_format_answer_single_col_scalar_float():
    """Scalar float result."""
    result = _format_answer("q", ["score"], [{"score": 3.14}])
    assert "3.14" in result
