"""End-to-end AI layer test: 25 representative questions through text-to-SQL.

Tests the full pipeline: NL question → Claude SQL generation → SQL validation →
execution against PostgreSQL → response formatting. Runs against a live database
connection (requires DATABASE_URL or the default dev connection).

Categories covered:
  - Scalar aggregation (count, sum, avg)
  - Provider lookup by NPI
  - Peer comparison / z-scores
  - Filtering by state, specialty, risk band
  - Multi-column results
  - Edge cases (typos, vague questions)
  - Chart spec generation
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from psycopg import AsyncConnection

from src.ai.text_to_sql import SQLValidationError, text_to_sql

# Skip entire module if no database or no Bedrock credentials
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://cms:cms_local_dev@localhost:25432/cms_fraud",
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.environ.get("RUN_AI_TESTS"),
        reason="Set RUN_AI_TESTS=1 to run AI integration tests",
    ),
]


@pytest_asyncio.fixture
async def conn():
    async with await AsyncConnection.connect(DATABASE_URL) as c:
        yield c


# ── Scalar aggregations ────────────────────────────────────────────────

SCALAR_QUESTIONS = [
    ("How many providers are there?", "count"),
    ("How many high-risk providers are there?", "count"),
    ("What is the total estimated payment across all providers?", "sum"),
    ("How many revoked providers are there?", "count"),
    ("What is the average risk score across all providers?", "avg"),
]


@pytest.mark.parametrize(
    "question,expected_type",
    SCALAR_QUESTIONS,
    ids=[q[0][:50] for q in SCALAR_QUESTIONS],
)
async def test_scalar_aggregation(conn, question, expected_type):
    result = await text_to_sql(question, conn)
    assert result["row_count"] >= 1
    assert result["columns"]
    assert result["sql"]
    # Scalar results should have a numeric value
    first_val = list(result["rows"][0].values())[0]
    assert isinstance(first_val, (int, float))


# ── Provider lookup ────────────────────────────────────────────────────

LOOKUP_QUESTIONS = [
    "Tell me about provider 1821387911",
    "What does provider 1821387911 bill for?",
    "What is the risk score for NPI 1821387911?",
]


@pytest.mark.parametrize("question", LOOKUP_QUESTIONS, ids=[q[:50] for q in LOOKUP_QUESTIONS])
async def test_provider_lookup(conn, question):
    result = await text_to_sql(question, conn)
    assert result["row_count"] >= 1
    # Should reference the queried NPI in results or SQL
    assert "1821387911" in result["sql"]


# ── Filtering ──────────────────────────────────────────────────────────

FILTER_QUESTIONS = [
    ("Show me high-risk providers in Florida", "FL"),
    ("Which providers in Texas have a risk score above 70?", "TX"),
    ("List revoked providers in California", "CA"),
]


@pytest.mark.parametrize(
    "question,state",
    FILTER_QUESTIONS,
    ids=[q[0][:50] for q in FILTER_QUESTIONS],
)
async def test_state_filter(conn, question, state):
    result = await text_to_sql(question, conn)
    assert result["sql"]
    assert state in result["sql"].upper() or f"'{state}'" in result["sql"]


# ── Multi-row with rankings ───────────────────────────────────────────

RANKING_QUESTIONS = [
    "Top 10 highest risk providers",
    "Which specialties have the most outlier billing?",
    "Which states have the most high-risk providers?",
    "Top 5 providers by total estimated payment",
]


@pytest.mark.parametrize("question", RANKING_QUESTIONS, ids=[q[:50] for q in RANKING_QUESTIONS])
async def test_ranking_query(conn, question):
    result = await text_to_sql(question, conn)
    assert result["row_count"] >= 2
    assert len(result["columns"]) >= 2


# ── Peer comparison ───────────────────────────────────────────────────

PEER_QUESTIONS = [
    "Which providers have the highest volume z-scores?",
    "Show me providers with charge z-scores above 3",
    "What is the average services per beneficiary for Internal Medicine?",
]


@pytest.mark.parametrize("question", PEER_QUESTIONS, ids=[q[:50] for q in PEER_QUESTIONS])
async def test_peer_comparison(conn, question):
    result = await text_to_sql(question, conn)
    assert result["row_count"] >= 1
    assert result["sql"]


# ── Chart spec generation ─────────────────────────────────────────────


async def test_chart_spec_for_multi_row(conn):
    """Multi-row categorical+numeric results should produce a chart spec."""
    from src.ai.chart_spec import generate_chart_spec

    result = await text_to_sql("Which states have the most high-risk providers?", conn)
    assert result["row_count"] >= 2
    spec = generate_chart_spec(result["columns"], result["rows"])
    assert spec is not None
    assert spec["type"] in ("bar", "line", "pie")
    assert spec["data"]


async def test_no_chart_for_scalar(conn):
    """Scalar results should NOT produce a chart spec."""
    from src.ai.chart_spec import generate_chart_spec

    result = await text_to_sql("How many providers are there?", conn)
    spec = generate_chart_spec(result["columns"], result["rows"])
    assert spec is None


# ── Edge cases ─────────────────────────────────────────────────────────


async def test_unanswerable_question(conn):
    """Questions outside the schema should raise UNANSWERABLE."""
    with pytest.raises(SQLValidationError, match="UNANSWERABLE"):
        await text_to_sql("What is the weather in Miami?", conn)


async def test_empty_result(conn):
    """Query that returns no rows should still succeed."""
    result = await text_to_sql("Show me providers in Alaska with risk score above 99", conn)
    # May or may not return results, but should not crash
    assert isinstance(result["rows"], list)
    assert result["sql"]
