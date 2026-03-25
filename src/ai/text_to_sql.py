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
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE"
    r"|UNION"  # prevents UNION-based data exfiltration
    r"|COPY|LOAD|IMPORT"  # bulk data operations
    r"|pg_sleep|pg_read_file|pg_read_binary_file|lo_import|lo_export"  # server-side abuse
    r"|dblink|dblink_exec"  # cross-database queries
    r"|set\s+role|set\s+session"  # privilege escalation
    r")\b",
    re.IGNORECASE,
)

# SQL comments can hide malicious keywords from pattern matching
_COMMENT_PATTERN = re.compile(r"(--|/\*)")

# Must start with SELECT or WITH (for CTEs)
_ALLOWED_START = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)

# Multiple statements via semicolons (beyond trailing)
_MULTI_STATEMENT = re.compile(r";.+", re.DOTALL)


class SQLValidationError(Exception):
    """Raised when generated SQL fails safety checks."""


def validate_sql(sql: str) -> str:
    """Validate and sanitize generated SQL. Returns cleaned SQL or raises."""
    cleaned = sql.strip().rstrip(";").strip()

    if not cleaned:
        raise SQLValidationError("Empty SQL generated")

    if cleaned.upper() == "UNANSWERABLE":
        raise SQLValidationError("UNANSWERABLE")

    # Block SQL comments (can hide malicious keywords)
    if _COMMENT_PATTERN.search(cleaned):
        raise SQLValidationError("SQL comments are not allowed")

    # Block multi-statement injection (semicolons within the query)
    if _MULTI_STATEMENT.search(cleaned):
        raise SQLValidationError("Multiple statements are not allowed")

    # Check forbidden keywords BEFORE the SELECT/WITH check so that
    # dangerous statements (DROP, DELETE) are caught even when
    # provider_context would treat them as direct answers.
    stripped = re.sub(r"'[^']*'", "''", cleaned)
    forbidden = _FORBIDDEN_PATTERNS.search(stripped)
    if forbidden:
        raise SQLValidationError(f"Forbidden keyword: {forbidden.group()}")

    if not _ALLOWED_START.match(cleaned):
        raise SQLValidationError(f"SQL must start with SELECT or WITH, got: {cleaned[:50]}")

    # Add LIMIT if missing
    if not re.search(r"\bLIMIT\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {MAX_ROWS}"

    return cleaned


async def text_to_sql(
    question: str,
    conn: AsyncConnection,
    *,
    history: list[dict[str, str]] | None = None,
    provider_context: str | None = None,
    model: str = CHAT_MODEL,
) -> dict[str, Any]:
    """Convert natural language question to SQL, execute, return results.

    When provider_context is supplied, Claude may answer directly from the
    context without generating SQL. If the response is not valid SQL,
    we return it as a direct text answer instead of raising.

    Returns dict with keys:
        - answer: formatted text answer
        - sql: the generated SQL query (None for direct answers)
        - columns: list of column names
        - rows: list of row dicts
        - row_count: number of rows returned
        - duration_ms: query execution time
    """
    system_prompt = build_text_to_sql_system_prompt()
    if provider_context:
        system_prompt += (
            "\n\n## Current Provider Context\n"
            f"{provider_context}\n\n"
            "Answer directly from this context when the data is sufficient. "
            "Only generate a SQL query when the question requires data NOT "
            "shown above (e.g. peer comparisons, state-level aggregates, "
            "other providers). For direct answers, respond with natural "
            "language \u2014 no SQL."
        )

    # Build messages with conversation history for context
    messages: list[dict[str, str]] = []
    if history:
        messages.extend(history[-6:])  # last 3 turns max to limit tokens
    messages.append({"role": "user", "content": question})

    # Ask Claude to generate SQL
    response = await invoke(
        messages=messages,
        system=system_prompt,
        model=model,
        max_tokens=512,
        temperature=0.0,
    )

    raw_response = response["text"].strip()

    # Strip markdown code fences if present
    cleaned = raw_response
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # Try to validate as SQL. If it fails and we have provider context,
    # treat natural-language responses as direct answers.
    try:
        sql = validate_sql(cleaned)
    except SQLValidationError as e:
        err_msg = str(e)
        is_natural_language = (
            "SQL must start with SELECT or WITH" in err_msg
            or "Empty SQL" in err_msg
            or "UNANSWERABLE" in err_msg
        )
        if provider_context and is_natural_language:
            logger.info("text_to_sql direct_answer question=%r", question[:80])
            return {
                "answer": raw_response,
                "sql": None,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "duration_ms": 0,
            }
        raise

    # Execute with timeout
    start = time.monotonic()
    async with conn.cursor() as cur:
        await cur.execute(f"SET statement_timeout = {int(QUERY_TIMEOUT_MS)}")
        await cur.execute(sql)
        columns = [desc.name for desc in cur.description] if cur.description else []
        raw_rows = await cur.fetchall()
        await cur.execute("RESET statement_timeout")

    duration_ms = int((time.monotonic() - start) * 1000)

    rows = [dict(zip(columns, row)) for row in raw_rows]

    # Build a text answer from the results
    answer = _format_answer(question, columns, rows)

    # For multi-row results, synthesize an insight summary via LLM
    if len(rows) > 1:
        synthesis = await _synthesize_results(question, columns, rows)
        if synthesis:
            answer = synthesis

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


_SYNTHESIS_PROMPT = (
    "You are a CMS fraud analyst assistant. "
    "Summarize these query results in 2-3 sentences. "
    "Highlight the most notable patterns. Be specific with numbers. "
    "Do not use markdown formatting."
)


async def _synthesize_results(
    question: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> str | None:
    """Generate an LLM summary for multi-row query results.

    Returns a 2-3 sentence synthesis, or None on failure (non-fatal).
    """
    # Serialize top rows as a compact table for the LLM
    display_rows = rows[:10]
    header = " | ".join(columns)
    lines = [header]
    for row in display_rows:
        lines.append(" | ".join(str(row.get(c, "")) for c in columns))
    if len(rows) > 10:
        lines.append(f"... ({len(rows)} total rows)")
    table = "\n".join(lines)

    user_msg = f"Question: {question}\n\nResults:\n{table}"

    try:
        response = await invoke(
            messages=[{"role": "user", "content": user_msg}],
            system=_SYNTHESIS_PROMPT,
            model=CHAT_MODEL,
            max_tokens=150,
            temperature=0.2,
        )
        return str(response["text"]).strip()
    except Exception:
        logger.exception("Result synthesis failed, falling back to count")
        return None
