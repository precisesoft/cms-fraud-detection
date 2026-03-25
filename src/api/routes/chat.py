"""Chat endpoint — natural language questions answered via text-to-SQL.

POST /api/chat accepts a message + conversation history, routes the question
through the text-to-SQL engine, and returns a structured response with the
answer, SQL used, and result data.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg import AsyncConnection

from src.ai.chart_spec import generate_chart_spec
from src.ai.text_to_sql import SQLValidationError, text_to_sql
from src.api.auth import get_current_user
from src.api.deps import get_db, get_readonly_db
from src.api.routes.audit import write_audit_entry
from src.api.schemas import AuditEventType, ChatRequest, ChatResponse, UserResponse

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
    request: Request,
    conn: AsyncConnection = Depends(get_readonly_db),
    write_conn: AsyncConnection = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> ChatResponse:
    """Answer a natural language question about the CMS data.

    Routes the question through text-to-SQL: generates SQL via Claude,
    validates it, executes against PostgreSQL, and returns results.
    """
    history = [{"role": m.role, "content": m.content} for m in req.history] or None

    try:
        result = await text_to_sql(req.message, conn, history=history)
    except SQLValidationError as e:
        if "UNANSWERABLE" in str(e):
            return ChatResponse(
                answer=(
                    "I can't answer that from the available data. "
                    "The dataset contains annual aggregated Medicare billing "
                    "(total services, charges, payments, peer z-scores, risk scores) "
                    "— not individual claim records or dates. "
                    'Try: "What does this provider bill for?", '
                    '"Which providers have the highest risk?", or '
                    '"Compare charges for code 99213 by state."'
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

    serialized_rows = [_serialize_row(r) for r in result["rows"]]
    chart = generate_chart_spec(result["columns"], serialized_rows)

    await write_audit_entry(
        write_conn,
        event_type=AuditEventType.query,
        analyst=getattr(current_user, "username", "system"),
        action="TEXT_TO_SQL_QUERY",
        entity_type="chat",
        entity_id=None,
        details={"message": req.message, "sql": result["sql"]},
        ip_address=request.client.host if request.client else None,
    )
    await write_conn.commit()

    return ChatResponse(
        answer=result["answer"],
        sql=result["sql"],
        columns=result["columns"],
        rows=serialized_rows,
        row_count=result["row_count"],
        duration_ms=result["duration_ms"],
        chart_spec=chart,
    )
