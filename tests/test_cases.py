"""Tests for case actions endpoint — investigation workflow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


def _mock_request(host: str = "127.0.0.1"):
    return MagicMock(client=MagicMock(host=host))


# ---------------------------------------------------------------------------
# record_action tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_action_success():
    """Real case — NPI resolved from provider_service_cases."""
    conn, cur = _mock_conn(None)
    cur.fetchone = AsyncMock(return_value=("1234567890",))
    req = CaseActionRequest(action=CaseAction.flagged, notes="Suspicious billing")

    with patch("src.api.routes.cases.write_audit_entry", new_callable=AsyncMock) as mock_audit:
        result = await record_action("case-001", req, _mock_request(), conn)

    assert result.case_id == "case-001"
    assert result.action == CaseAction.flagged
    assert "FLAGGED" in result.message
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_action_simulated_case():
    """Simulated case — NPI extracted from pipe-delimited case_id."""
    conn, cur = _mock_conn(None)
    cur.fetchone = AsyncMock(return_value=None)
    req = CaseActionRequest(action=CaseAction.approved)

    with patch("src.api.routes.cases.write_audit_entry", new_callable=AsyncMock):
        result = await record_action("1760461826|99215|O", req, _mock_request(), conn)

    assert result.case_id == "1760461826|99215|O"
    assert result.action == CaseAction.approved
    assert "APPROVED" in result.message


@pytest.mark.asyncio
async def test_record_action_all_types():
    """Verify all action types are accepted."""
    for action in CaseAction:
        conn, cur = _mock_conn(None)
        cur.fetchone = AsyncMock(return_value=("1234567890",))
        req = CaseActionRequest(action=action)
        with patch("src.api.routes.cases.write_audit_entry", new_callable=AsyncMock):
            result = await record_action("case-001", req, _mock_request(), conn)
        assert result.action == action


@pytest.mark.asyncio
async def test_record_action_empty_npi_raises_400():
    """When case_id has no pipe and DB returns None, npi becomes '' → 400 (line 50)."""
    conn, cur = _mock_conn(None)
    cur.fetchone = AsyncMock(return_value=None)
    req = CaseActionRequest(action=CaseAction.flagged)

    from fastapi import HTTPException

    # case_id with no NPI prefix — split("|")[0] is the whole string which is non-empty
    # To trigger the empty-npi path we need case_id="" so split gives [""]
    with pytest.raises(HTTPException) as exc_info:
        await record_action("", req, _mock_request(), conn)

    assert exc_info.value.status_code == 400
    assert "Cannot resolve NPI" in exc_info.value.detail


@pytest.mark.asyncio
async def test_record_action_writes_audit_entry_details():
    conn, cur = _mock_conn(None)
    cur.fetchone = AsyncMock(return_value=("1234567890",))
    req = CaseActionRequest(action=CaseAction.escalated, notes="Needs supervisor review")

    with patch("src.api.routes.cases.write_audit_entry", new_callable=AsyncMock) as mock_audit:
        await record_action("case-001", req, _mock_request(), conn)

    _, kwargs = mock_audit.await_args
    assert kwargs["event_type"].value == "CASE_ACTION"
    assert kwargs["action"] == "ESCALATED"
    assert kwargs["entity_type"] == "case"
    assert kwargs["entity_id"] == "case-001"
    assert kwargs["details"] == {"npi": "1234567890", "notes": "Needs supervisor review"}


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
