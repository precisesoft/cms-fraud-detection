"""Chat endpoint — natural language questions answered via text-to-SQL.

POST /api/chat accepts a message + conversation history, routes the question
through the text-to-SQL engine, and returns a structured response with the
answer, SQL used, and result data.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from src.ai.text_to_sql import SQLValidationError, text_to_sql
from src.api.deps import get_db
from src.api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _serialize_row(row: dict) -> dict[str, object]:
    """Ensure all row values are JSON-serializable."""
    out: dict[str, object] = {}
    for k, v in row.items():
        if isinstance(v, float):
            out[k] = round(v, 4) if v == v else None  # handle NaN
        elif isinstance(v, (int, str, bool, type(None))):
            out[k] = v
        else:
            out[k] = str(v)
    return out


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    conn: AsyncConnection = Depends(get_db),
) -> ChatResponse:
    """Answer a natural language question about the CMS data.

    Routes the question through text-to-SQL: generates SQL via Claude,
    validates it, executes against PostgreSQL, and returns results.
    """
    try:
        result = await text_to_sql(req.message, conn)
    except SQLValidationError as e:
        if "UNANSWERABLE" in str(e):
            return ChatResponse(
                answer=(
                    "I can't answer that question from the available data. "
                    "Try asking about providers, claims, risk scores, "
                    "billing patterns, or peer comparisons."
                ),
            )
        logger.warning("SQL validation failed: %s", e)
        raise HTTPException(
            status_code=422,
            detail=f"Could not generate a valid query: {e}",
        ) from e
    except Exception:
        logger.exception("Chat query failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your question. Please try rephrasing.",
        ) from None

    return ChatResponse(
        answer=result["answer"],
        sql=result["sql"],
        columns=result["columns"],
        rows=[_serialize_row(r) for r in result["rows"]],
        row_count=result["row_count"],
        duration_ms=result["duration_ms"],
    )
