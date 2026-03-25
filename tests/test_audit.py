"""Tests for audit trail helpers and endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.routes.audit import list_audit_entries, write_audit_entry
from src.api.schemas import AuditEventType


class _FakeCursorCtx:
    def __init__(self, cur: AsyncMock):
        self._cur = cur

    async def __aenter__(self):
        return self._cur

    async def __aexit__(self, *args):
        pass


def _mock_conn(fetchone=None, fetchall=None):
    cur = AsyncMock()
    cur.fetchone = AsyncMock(return_value=fetchone)
    cur.fetchall = AsyncMock(return_value=fetchall or [])
    conn = AsyncMock()
    conn.cursor = MagicMock(return_value=_FakeCursorCtx(cur))
    conn.commit = AsyncMock()
    return conn, cur


@pytest.mark.asyncio
async def test_write_audit_entry_returns_model():
    conn, cur = _mock_conn(
        fetchone=(
            7,
            "QUERY",
            "chat",
            None,
            "analyst",
            "TEXT_TO_SQL_QUERY",
            {"message": "How many providers?"},
            "127.0.0.1",
            "2026-03-24T10:30:00+00:00",
        )
    )

    entry = await write_audit_entry(
        conn,
        event_type=AuditEventType.query,
        analyst="analyst",
        action="TEXT_TO_SQL_QUERY",
        entity_type="chat",
        details={"message": "How many providers?"},
        ip_address="127.0.0.1",
    )

    assert entry.id == 7
    assert entry.event_type == AuditEventType.query
    assert entry.analyst == "analyst"
    assert entry.details["message"] == "How many providers?"
    cur.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_audit_entries_filters_and_counts():
    rows = [
        (
            9,
            "CASE_ACTION",
            "case",
            "case-001",
            "demo-analyst",
            "FLAGGED",
            {"npi": "1234567890"},
            "127.0.0.1",
            "2026-03-24T10:30:00+00:00",
        )
    ]
    conn, cur = _mock_conn(fetchall=rows)

    result = await list_audit_entries(
        entity_id="case-001",
        analyst="demo-analyst",
        event_type=AuditEventType.case_action,
        limit=25,
        conn=conn,
    )

    assert result.count == 1
    assert result.entries[0].entity_id == "case-001"
    assert result.entries[0].event_type == AuditEventType.case_action
    execute_args = cur.execute.await_args.args
    assert "WHERE entity_id = %s AND analyst = %s AND event_type = %s" in execute_args[0]
    assert execute_args[1] == ("case-001", "demo-analyst", "CASE_ACTION", 25)
