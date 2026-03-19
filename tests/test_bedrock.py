"""Tests for Bedrock client wrapper and prompts module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.ai.bedrock import invoke
from src.ai.prompts import FEW_SHOT_EXAMPLES, build_text_to_sql_system_prompt

# ---------------------------------------------------------------------------
# Bedrock client tests
# ---------------------------------------------------------------------------


def _make_response(text: str = "hello", input_tokens: int = 10, output_tokens: int = 5):
    """Build a mock Bedrock invoke_model response."""
    body = json.dumps(
        {
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        }
    ).encode()
    mock_body = MagicMock()
    mock_body.read.return_value = body
    return {"body": mock_body}


@pytest.mark.asyncio
async def test_invoke_success():
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = _make_response("SELECT 1;")

    with patch("src.ai.bedrock._get_client", return_value=mock_client):
        result = await invoke(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=100,
        )

    assert result["text"] == "SELECT 1;"
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 5
    assert result["stop_reason"] == "end_turn"
    mock_client.invoke_model.assert_called_once()


@pytest.mark.asyncio
async def test_invoke_with_system_prompt():
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = _make_response("ok")

    with patch("src.ai.bedrock._get_client", return_value=mock_client):
        await invoke(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful.",
        )

    call_body = json.loads(mock_client.invoke_model.call_args.kwargs["body"])
    assert call_body["system"] == "You are helpful."


@pytest.mark.asyncio
async def test_invoke_retry_on_throttle():
    from botocore.exceptions import ClientError

    throttle_error = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "InvokeModel",
    )
    mock_client = MagicMock()
    mock_client.invoke_model.side_effect = [
        throttle_error,
        _make_response("retried"),
    ]

    with (
        patch("src.ai.bedrock._get_client", return_value=mock_client),
        patch("src.ai.bedrock.RETRY_BASE_DELAY", 0.01),
    ):
        result = await invoke(messages=[{"role": "user", "content": "test"}])

    assert result["text"] == "retried"
    assert mock_client.invoke_model.call_count == 2


@pytest.mark.asyncio
async def test_invoke_non_retryable_error():
    from botocore.exceptions import ClientError

    access_error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "No access"}},
        "InvokeModel",
    )
    mock_client = MagicMock()
    mock_client.invoke_model.side_effect = access_error

    with patch("src.ai.bedrock._get_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="AccessDeniedException"):
            await invoke(messages=[{"role": "user", "content": "test"}])


# ---------------------------------------------------------------------------
# Prompts tests
# ---------------------------------------------------------------------------


def test_system_prompt_contains_schema():
    prompt = build_text_to_sql_system_prompt()
    assert "provider_service_cases" in prompt
    assert "provider_features" in prompt
    assert "seed_risk_score" in prompt
    assert "UNANSWERABLE" in prompt


def test_system_prompt_contains_all_few_shots():
    prompt = build_text_to_sql_system_prompt()
    for ex in FEW_SHOT_EXAMPLES:
        assert ex["question"] in prompt
        assert ex["sql"] in prompt


def test_few_shots_are_select_only():
    for ex in FEW_SHOT_EXAMPLES:
        sql = ex["sql"].strip().upper()
        assert sql.startswith("SELECT"), f"Few-shot not a SELECT: {ex['question']}"
        for bad in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"):
            assert bad not in sql, f"Few-shot contains {bad}: {ex['question']}"
