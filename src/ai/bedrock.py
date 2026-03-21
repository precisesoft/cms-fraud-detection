"""AWS Bedrock client wrapper for Claude model invocations.

Provides an async interface over the synchronous boto3 bedrock-runtime client
using run_in_executor. Includes retry with exponential backoff and token tracking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# Model IDs — configurable via env vars
CHAT_MODEL = os.getenv("BEDROCK_CHAT_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
NARRATIVE_MODEL = os.getenv("BEDROCK_NARRATIVE_MODEL", "us.anthropic.claude-sonnet-4-6")

ANTHROPIC_VERSION = "bedrock-2023-05-31"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


@lru_cache(maxsize=1)
def _get_client():  # type: ignore[no-untyped-def]
    """Create a singleton bedrock-runtime client."""
    region = os.getenv("AWS_REGION", "us-east-1")
    config = Config(
        region_name=region,
        retries={"max_attempts": 0},  # we handle retries ourselves
        read_timeout=60,
        connect_timeout=5,
    )
    return boto3.client("bedrock-runtime", config=config)


async def invoke(
    *,
    messages: list[dict[str, str]],
    system: str | None = None,
    model: str = CHAT_MODEL,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Invoke a Claude model on Bedrock and return the parsed response.

    Returns dict with keys: text, input_tokens, output_tokens, stop_reason.
    Raises RuntimeError on exhausted retries.
    """
    body: dict[str, Any] = {
        "anthropic_version": ANTHROPIC_VERSION,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system:
        body["system"] = system

    payload = json.dumps(body).encode()
    client = _get_client()
    loop = asyncio.get_running_loop()

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.invoke_model(
                    modelId=model,
                    contentType="application/json",
                    accept="application/json",
                    body=payload,
                ),
            )
            result = json.loads(response["body"].read())

            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text += block["text"]

            usage = result.get("usage", {})
            logger.info(
                "Bedrock invoke OK model=%s input_tokens=%d output_tokens=%d",
                model,
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )

            return {
                "text": text,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "stop_reason": result.get("stop_reason", "unknown"),
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            last_error = e
            if error_code in ("ThrottlingException", "ServiceUnavailableException"):
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Bedrock %s (attempt %d/%d), retrying in %.1fs",
                    error_code,
                    attempt,
                    MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                raise RuntimeError(f"Bedrock error: {error_code} — {e}") from e
        except BotoCoreError as e:
            # ConnectionClosedError, EndpointConnectionError, etc.
            last_error = e
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Bedrock connection error %s (attempt %d/%d), retrying in %.1fs",
                type(e).__name__,
                attempt,
                MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)

    raise RuntimeError(f"Bedrock invoke failed after {MAX_RETRIES} retries: {last_error}")
