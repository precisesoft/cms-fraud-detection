"""Audit trail endpoints and helpers for analyst accountability."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from psycopg import AsyncConnection

from src.api.auth import get_current_user
from src.api.deps import get_db
from src.api.schemas import (
    AuditEntry,
    AuditEntryCreateRequest,
    AuditEventType,
    AuditListResponse,
    UserResponse,
)

router = APIRouter(prefix="/audit", tags=["audit"])


async def write_audit_entry(
    conn: AsyncConnection,
    *,
    event_type: AuditEventType,
    analyst: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditEntry:
    """Write an audit entry using the existing transaction on the connection."""
    async with conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO audit_log (
                event_type,
                entity_type,
                entity_id,
                analyst,
                action,
                details,
                ip_address
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING id, event_type, entity_type, entity_id, analyst, action,
                      details, host(ip_address) AS ip_address,
                      created_at::text AS created_at
            """,
            (
                event_type.value,
                entity_type,
                entity_id,
                analyst,
                action,
                json.dumps(details or {}),
                ip_address,
            ),
        )
        row = await cur.fetchone()

    if row is None:
        raise RuntimeError("Audit entry insert did not return a row")

    return AuditEntry(
        id=row[0],
        event_type=AuditEventType(row[1]),
        entity_type=row[2],
        entity_id=row[3],
        analyst=row[4],
        action=row[5],
        details=row[6] or {},
        ip_address=row[7],
        created_at=row[8],
    )


@router.post("", response_model=AuditEntry)
async def create_audit_entry(
    payload: AuditEntryCreateRequest,
    request: Request,
    conn: AsyncConnection = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> AuditEntry:
    """Create a manual audit entry for internal workflows and admin tools."""
    entry = await write_audit_entry(
        conn,
        event_type=payload.event_type,
        analyst=getattr(current_user, "username", "system"),
        action=payload.action,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        details=payload.details,
        ip_address=request.client.host if request.client else None,
    )
    await conn.commit()
    return entry


@router.get("", response_model=AuditListResponse)
async def list_audit_entries(
    entity_id: str | None = None,
    analyst: str | None = None,
    event_type: AuditEventType | None = None,
    limit: int = 50,
    conn: AsyncConnection = Depends(get_db),
) -> AuditListResponse:
    """List recent audit entries with optional analyst/entity filters."""
    where_clauses: list[str] = []
    params: list[str | int] = []

    if entity_id:
        where_clauses.append("entity_id = %s")
        params.append(entity_id)
    if analyst:
        where_clauses.append("analyst = %s")
        params.append(analyst)
    if event_type:
        where_clauses.append("event_type = %s")
        params.append(event_type.value)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    async with conn.cursor() as cur:
        await cur.execute(
            f"""
            SELECT id, event_type, entity_type, entity_id, analyst, action,
                   details, host(ip_address) AS ip_address,
                   created_at::text AS created_at
            FROM audit_log
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (*params, limit),
        )
        rows = await cur.fetchall()

    entries = [
        AuditEntry(
            id=row[0],
            event_type=AuditEventType(row[1]),
            entity_type=row[2],
            entity_id=row[3],
            analyst=row[4],
            action=row[5],
            details=row[6] or {},
            ip_address=row[7],
            created_at=row[8],
        )
        for row in rows
    ]
    return AuditListResponse(entries=entries, count=len(entries))
