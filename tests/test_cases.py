"""Tests for case actions endpoint — investigation workflow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.api.routes.cases import list_actions, list_pending, record_action
from src.api.schemas import CaseAction, CaseActionRequest


class _FakeCursorCtx:
    """Async context manager that always returns the same cursor mock."""

    def __init__(self, cur: AsyncMock):
        self._cur = cur

    async def __aenter__(self):
        return self._cur

    async def __aexit__(self, *args):
        pass


def _mock_conn(rows, description=None):
    """Build mock async connection with cursor context manager."""
    cur = AsyncMock()
    cur.fetchone = AsyncMock(
        return_value=rows if isinstance(rows, tuple) else (rows,) if rows else None
    )
    cur.fetchall = AsyncMock(return_value=rows if isinstance(rows, list) else [])
    cur.description = description
    conn = AsyncMock()
    conn.cursor = MagicMock(return_value=_FakeCursorCtx(cur))
    conn.commit = AsyncMock()
    return conn, cur


# ---------------------------------------------------------------------------
# record_action tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_action_success():
    conn, cur = _mock_conn((1,))
    # First fetchone returns case exists, second returns insert id
    cur.fetchone = AsyncMock(side_effect=[(1,), (42,)])
    req = CaseActionRequest(action=CaseAction.flagged, notes="Suspicious billing")

    result = await record_action("case-001", req, conn)

    assert result.case_id == "case-001"
    assert result.action == CaseAction.flagged
    assert "FLAGGED" in result.message


@pytest.mark.asyncio
async def test_record_action_case_not_found():
    conn, cur = _mock_conn(None)
    cur.fetchone = AsyncMock(return_value=None)
    req = CaseActionRequest(action=CaseAction.approved)

    with pytest.raises(HTTPException) as exc_info:
        await record_action("nonexistent", req, conn)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_record_action_all_types():
    """Verify all action types are accepted."""
    for action in CaseAction:
        conn, cur = _mock_conn((1,))
        cur.fetchone = AsyncMock(side_effect=[(1,), (1,)])
        req = CaseActionRequest(action=action)
        result = await record_action("case-001", req, conn)
        assert result.action == action


# ---------------------------------------------------------------------------
# list_actions tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_actions_with_history():
    desc = [
        MagicMock(name=n)
        for n in ["id", "case_id", "npi", "action", "notes", "analyst_id", "created_at"]
    ]
    for d, n in zip(desc, ["id", "case_id", "npi", "action", "notes", "analyst_id", "created_at"]):
        d.name = n
    rows = [
        (
            2,
            "case-001",
            "1234567890",
            "FLAGGED",
            "Review needed",
            "demo-analyst",
            "2026-03-20T10:00:00",
        ),
        (1, "case-001", "1234567890", "APPROVED", None, "demo-analyst", "2026-03-20T09:00:00"),
    ]
    conn, cur = _mock_conn(rows, description=desc)

    result = await list_actions("case-001", conn)

    assert result.case_id == "case-001"
    assert len(result.actions) == 2
    assert result.current_status == CaseAction.flagged


@pytest.mark.asyncio
async def test_list_actions_empty():
    desc = [
        MagicMock(name=n)
        for n in ["id", "case_id", "npi", "action", "notes", "analyst_id", "created_at"]
    ]
    for d, n in zip(desc, ["id", "case_id", "npi", "action", "notes", "analyst_id", "created_at"]):
        d.name = n
    conn, cur = _mock_conn([], description=desc)

    result = await list_actions("case-001", conn)

    assert result.actions == []
    assert result.current_status is None


# ---------------------------------------------------------------------------
# list_pending tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_pending():
    desc = [
        MagicMock(name=n)
        for n in [
            "case_id",
            "npi",
            "provider_last_org_name",
            "hcpcs_cd",
            "hcpcs_desc",
            "seed_risk_score",
            "seed_case_label",
            "avg_submitted_charge",
            "tot_srvcs",
        ]
    ]
    for d, n in zip(
        desc,
        [
            "case_id",
            "npi",
            "provider_last_org_name",
            "hcpcs_cd",
            "hcpcs_desc",
            "seed_risk_score",
            "seed_case_label",
            "avg_submitted_charge",
            "tot_srvcs",
        ],
    ):
        d.name = n
    rows = [
        (
            "case-100",
            "1111111111",
            "Smith Clinic",
            "99215",
            "Office visit",
            85,
            "high_risk",
            450.0,
            800,
        ),
    ]
    conn, cur = _mock_conn(rows, description=desc)

    result = await list_pending(limit=10, conn=conn)

    assert len(result) == 1
    assert result[0]["case_id"] == "case-100"
    assert result[0]["seed_risk_score"] == 85


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_case_action_enum():
    assert CaseAction.approved == "APPROVED"
    assert CaseAction.flagged == "FLAGGED"
    assert CaseAction.denied == "DENIED"
    assert CaseAction.escalated == "ESCALATED"


def test_case_action_request_validation():
    req = CaseActionRequest(action=CaseAction.flagged, notes="test")
    assert req.action == CaseAction.flagged
    assert req.notes == "test"


def test_case_action_request_no_notes():
    req = CaseActionRequest(action=CaseAction.approved)
    assert req.notes is None
