"""Deterministic chart spec generator for text-to-SQL results.

Analyzes query result shape (columns, rows) and produces a Recharts-compatible
JSON spec when the data is chart-worthy. No LLM call — purely rule-based.
"""

from __future__ import annotations

import re
from typing import Any

# Column name patterns that indicate time-series data
_TIME_PATTERNS = re.compile(
    r"(year|month|quarter|date|week|period|time)", re.IGNORECASE
)

# Column name patterns that indicate categorical data
_CATEGORICAL_PATTERNS = re.compile(
    r"(state|specialty|type|band|label|category|reason|name|provider_type"
    r"|risk_band|entity_code|place_of_service|hcpcs)",
    re.IGNORECASE,
)

# Column name patterns for share/proportion data (good for pie charts)
_SHARE_PATTERNS = re.compile(
    r"(share|pct|percent|fraction|ratio|rate|proportion)", re.IGNORECASE
)

# Minimum rows to warrant a chart
MIN_CHART_ROWS = 2
MAX_PIE_SLICES = 8


def generate_chart_spec(
    columns: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return a Recharts-compatible chart spec, or None if data isn't chart-worthy."""
    if len(rows) < MIN_CHART_ROWS or len(columns) < 2:
        return None

    cat_cols = [c for c in columns if _is_categorical(c, rows)]
    num_cols = [c for c in columns if _is_numeric(c, rows)]
    time_cols = [c for c in columns if _TIME_PATTERNS.search(c)]

    if not num_cols:
        return None

    # Time-series → line chart
    if time_cols:
        x_key = time_cols[0]
        y_key = _best_numeric(num_cols, exclude={x_key})
        if y_key:
            return _line_spec(x_key, y_key, rows)

    # Small categorical + single share/proportion column → pie
    if (
        cat_cols
        and len(rows) <= MAX_PIE_SLICES
        and len(num_cols) == 1
        and _SHARE_PATTERNS.search(num_cols[0])
    ):
        return _pie_spec(cat_cols[0], num_cols[0], rows)

    # Categorical + numeric → bar chart (most common case)
    if cat_cols:
        x_key = cat_cols[0]
        y_key = _best_numeric(num_cols, exclude={x_key})
        if y_key:
            return _bar_spec(x_key, y_key, rows)

    # Fallback: first column as x, first numeric as y → bar
    x_key = columns[0]
    if columns[0] != num_cols[0]:
        y_key = num_cols[0]
    elif len(num_cols) > 1:
        y_key = num_cols[1]
    else:
        y_key = None
    if y_key:
        return _bar_spec(x_key, y_key, rows)

    return None


def _is_categorical(col: str, rows: list[dict[str, Any]]) -> bool:
    """Check if column values are categorical (strings)."""
    if _CATEGORICAL_PATTERNS.search(col):
        return True
    sample = [r.get(col) for r in rows[:5] if r.get(col) is not None]
    return bool(sample) and all(isinstance(v, str) for v in sample)


def _is_numeric(col: str, rows: list[dict[str, Any]]) -> bool:
    """Check if column values are numeric."""
    sample = [r.get(col) for r in rows[:5] if r.get(col) is not None]
    return bool(sample) and all(isinstance(v, (int, float)) for v in sample)


def _is_count_column(col: str) -> bool:
    return bool(re.search(r"(count|total|num|n_|sum)", col, re.IGNORECASE))


def _best_numeric(
    num_cols: list[str], exclude: set[str] | None = None
) -> str | None:
    """Pick the most interesting numeric column (prefer counts/scores/payments)."""
    exclude = exclude or set()
    candidates = [c for c in num_cols if c not in exclude]
    if not candidates:
        return None
    # Prefer columns with these keywords
    priority = ["count", "score", "payment", "total", "amount", "avg", "sum"]
    for keyword in priority:
        for c in candidates:
            if keyword in c.lower():
                return c
    return candidates[0]


def _format_title(x_key: str, y_key: str) -> str:
    """Generate a readable chart title from column names."""
    y_label = y_key.replace("_", " ").title()
    x_label = x_key.replace("_", " ").title()
    return f"{y_label} by {x_label}"


def _bar_spec(
    x_key: str, y_key: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    data = _prepare_data(rows, [x_key, y_key])
    return {
        "type": "bar",
        "title": _format_title(x_key, y_key),
        "xKey": x_key,
        "yKey": y_key,
        "data": data,
    }


def _line_spec(
    x_key: str, y_key: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    data = _prepare_data(rows, [x_key, y_key])
    return {
        "type": "line",
        "title": _format_title(x_key, y_key),
        "xKey": x_key,
        "yKey": y_key,
        "data": data,
    }


def _pie_spec(
    name_key: str, value_key: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    data = _prepare_data(rows, [name_key, value_key])
    return {
        "type": "pie",
        "title": value_key.replace("_", " ").title(),
        "nameKey": name_key,
        "valueKey": value_key,
        "data": data,
    }


def _prepare_data(
    rows: list[dict[str, Any]], keys: list[str]
) -> list[dict[str, Any]]:
    """Extract only the needed keys from rows, limit to 20 data points."""
    out: list[dict[str, Any]] = []
    for row in rows[:20]:
        entry: dict[str, Any] = {}
        for k in keys:
            v = row.get(k)
            if isinstance(v, float) and v != v:  # NaN check
                v = 0
            entry[k] = v
        out.append(entry)
    return out
