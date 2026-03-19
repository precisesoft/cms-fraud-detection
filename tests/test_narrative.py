"""Tests for risk narrative generator."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.ai.narrative import generate_narrative


@pytest.mark.asyncio
async def test_generate_narrative_success():
    mock_response = {
        "text": "This provider shows elevated risk due to revocation status.",
        "input_tokens": 200,
        "output_tokens": 30,
        "stop_reason": "end_turn",
    }

    with patch("src.ai.narrative.invoke", return_value=mock_response):
        result = await generate_narrative(
            npi="1821387911",
            risk_score=88,
            risk_band="high_risk",
            signals=[
                {
                    "name": "revoked_provider",
                    "direction": "risk",
                    "description": "Provider revoked",
                },
                {"name": "large_panel", "direction": "legitimacy", "description": "Large panel"},
            ],
            provider_name="Test Provider",
            provider_type="Internal Medicine",
            state="FL",
        )

    assert result is not None
    assert "revocation" in result.lower()


@pytest.mark.asyncio
async def test_generate_narrative_with_peer_comparisons():
    mock_response = {
        "text": "Provider charges are 4x peer average.",
        "input_tokens": 300,
        "output_tokens": 20,
        "stop_reason": "end_turn",
    }

    with patch("src.ai.narrative.invoke", return_value=mock_response) as mock_invoke:
        result = await generate_narrative(
            npi="1234567890",
            risk_score=60,
            risk_band="high_risk",
            signals=[],
            peer_comparisons=[
                {
                    "metric": "submitted_charge",
                    "provider_value": 400,
                    "peer_mean": 100,
                    "z_score": 3.5,
                },
            ],
        )

    assert result is not None
    # Verify peer data was included in the prompt
    call_args = mock_invoke.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "submitted_charge" in user_msg
    assert "400" in user_msg


@pytest.mark.asyncio
async def test_generate_narrative_handles_failure():
    with patch("src.ai.narrative.invoke", side_effect=RuntimeError("Bedrock down")):
        result = await generate_narrative(
            npi="1234567890",
            risk_score=50,
            risk_band="review",
            signals=[],
        )

    assert result is None  # non-fatal


@pytest.mark.asyncio
async def test_generate_narrative_includes_recommendation():
    mock_response = {
        "text": "DENY recommendation issued.",
        "input_tokens": 100,
        "output_tokens": 10,
        "stop_reason": "end_turn",
    }

    with patch("src.ai.narrative.invoke", return_value=mock_response) as mock_invoke:
        await generate_narrative(
            npi="1234567890",
            risk_score=80,
            risk_band="high_risk",
            signals=[],
            recommendation="deny",
        )

    user_msg = mock_invoke.call_args.kwargs["messages"][0]["content"]
    assert "DENY" in user_msg
