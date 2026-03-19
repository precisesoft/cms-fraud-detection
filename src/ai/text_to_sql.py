"""Text-to-SQL engine: natural language → validated SQL → executed results.

Accepts a natural language question, sends it to Claude with the schema prompt,
validates the generated SQL (SELECT only, no mutations), executes it against
PostgreSQL, and returns formatted results.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from psycopg import AsyncConnection

from src.ai.bedrock import CHAT_MODEL, invoke
from src.ai.prompts import build_text_to_sql_system_prompt

logger = logging.getLogger(__name__)

# Safety limits
MAX_ROWS = 500
QUERY_TIMEOUT_MS = 5000

# Patterns that must never appear in generated SQL
_FORBIDDEN_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

# Must start with SELECT or WITH (for CTEs)
_ALLOWED_START = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


class SQLValidationError(Exception):
    """Raised when generated SQL fails safety checks."""


def validate_sql(sql: str) -> str:
    """Validate and sanitize generated SQL. Returns cleaned SQL or raises."""
    cleaned = sql.strip().rstrip(";").strip()

    if not cleaned:
        raise SQLValidationError("Empty SQL generated")

    if cleaned.upper() == "UNANSWERABLE":
        raise SQLValidationError("UNANSWERABLE")

    if not _ALLOWED_START.match(cleaned):
        raise SQLValidationError(f"SQL must start with SELECT or WITH, got: {cleaned[:50]}")

    forbidden = _FORBIDDEN_PATTERNS.search(cleaned)
    if forbidden:
        raise SQLValidationError(f"Forbidden keyword: {forbidden.group()}")

    # Strip any trailing semicolons and add LIMIT if missing
    if not re.search(r"\bLIMIT\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {MAX_ROWS}"

    return cleaned


async def text_to_sql(
    question: str,
    conn: AsyncConnection,
    *,
    model: str = CHAT_MODEL,
) -> dict[str, Any]:
    """Convert natural language question to SQL, execute, return results.

    Returns dict with keys:
        - answer: formatted text answer
        - sql: the generated SQL query
        - columns: list of column names
        - rows: list of row dicts
        - row_count: number of rows returned
        - duration_ms: query execution time
    """
    system_prompt = build_text_to_sql_system_prompt()

    # Ask Claude to generate SQL
    response = await invoke(
        messages=[{"role": "user", "content": question}],
        system=system_prompt,
        model=model,
        max_tokens=512,
        temperature=0.0,
    )

    raw_sql = response["text"].strip()

    # Strip markdown code fences if present
    if raw_sql.startswith("```"):
        raw_sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql)
        raw_sql = re.sub(r"\s*```$", "", raw_sql)

    sql = validate_sql(raw_sql)

    # Execute with timeout
    start = time.monotonic()
    async with conn.cursor() as cur:
        await cur.execute(f"SET statement_timeout = '{QUERY_TIMEOUT_MS}'")
        await cur.execute(sql)
        columns = [desc.name for desc in cur.description] if cur.description else []
        raw_rows = await cur.fetchall()
        await cur.execute("RESET statement_timeout")

    duration_ms = int((time.monotonic() - start) * 1000)

    rows = [dict(zip(columns, row)) for row in raw_rows]

    # Build a text answer from the results
    answer = _format_answer(question, columns, rows)

    logger.info(
        "text_to_sql question=%r rows=%d duration=%dms sql=%s",
        question[:80],
        len(rows),
        duration_ms,
        sql[:200],
    )

    return {
        "answer": answer,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "duration_ms": duration_ms,
    }


def _format_answer(question: str, columns: list[str], rows: list[dict[str, Any]]) -> str:
    """Format query results into a human-readable text answer."""
    if not rows:
        return "No results found for your query."

    if len(rows) == 1 and len(columns) == 1:
        # Scalar result
        val = rows[0][columns[0]]
        return f"{_format_value(val)}"

    if len(rows) == 1:
        # Single row — describe each column
        row = rows[0]
        parts = [f"{col}: {_format_value(row[col])}" for col in columns]
        return ", ".join(parts)

    # Multiple rows — summarize
    return f"Found {len(rows)} results."


def _format_value(val: Any) -> str:
    """Format a single value for display."""
    if val is None:
        return "N/A"
    if isinstance(val, float):
        if abs(val) >= 1000:
            return f"{val:,.0f}"
        return f"{val:.2f}"
    return str(val)
