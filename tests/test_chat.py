"""Tests for chat endpoint — request/response validation and error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.ai.text_to_sql import SQLValidationError
from src.api.routes.chat import _serialize_row, chat
from src.api.schemas import ChatRequest

# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


def test_serialize_row_basic():
    row = {"name": "Smith", "score": 88, "active": True, "note": None}
    result = _serialize_row(row)
    assert result == row


def test_serialize_row_rounds_floats():
    row = {"value": 3.141592653}
    result = _serialize_row(row)
    assert result["value"] == 3.1416


def test_serialize_row_handles_nan():
    row = {"value": float("nan")}
    result = _serialize_row(row)
    assert result["value"] is None


def test_serialize_row_converts_unknown_types():
    from decimal import Decimal

    row = {"amount": Decimal("99.99")}
    result = _serialize_row(row)
    assert result["amount"] == "99.99"


# ---------------------------------------------------------------------------
# Endpoint tests (mocked text_to_sql)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_success():
    mock_result = {
        "answer": "42",
        "sql": "SELECT count(*) FROM provider_features",
        "columns": ["count"],
        "rows": [{"count": 42}],
        "row_count": 1,
        "duration_ms": 15,
    }

    with patch("src.api.routes.chat.text_to_sql", new_callable=AsyncMock, return_value=mock_result):
        req = ChatRequest(message="How many providers?")
        result = await chat(req, conn=AsyncMock())

    assert result.answer == "42"
    assert result.sql == "SELECT count(*) FROM provider_features"
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_chat_unanswerable():
    with patch(
        "src.api.routes.chat.text_to_sql",
        new_callable=AsyncMock,
        side_effect=SQLValidationError("UNANSWERABLE"),
    ):
        req = ChatRequest(message="What's the weather?")
        result = await chat(req, conn=AsyncMock())

    assert "can't answer" in result.answer.lower()
    assert result.sql is None


@pytest.mark.asyncio
async def test_chat_validation_error():
    from fastapi import HTTPException

    with patch(
        "src.api.routes.chat.text_to_sql",
        new_callable=AsyncMock,
        side_effect=SQLValidationError("SQL must start with SELECT"),
    ):
        req = ChatRequest(message="DROP everything")
        with pytest.raises(HTTPException) as exc_info:
            await chat(req, conn=AsyncMock())

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_chat_internal_error():
    from fastapi import HTTPException

    with patch(
        "src.api.routes.chat.text_to_sql",
        new_callable=AsyncMock,
        side_effect=RuntimeError("DB exploded"),
    ):
        req = ChatRequest(message="Show providers")
        with pytest.raises(HTTPException) as exc_info:
            await chat(req, conn=AsyncMock())

    assert exc_info.value.status_code == 500
