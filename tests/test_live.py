"""Tests for GET /api/live/stream — SSE endpoint with mocked DB."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.routes.live import router

# ---------------------------------------------------------------------------
# Fake DB row matching provider_service_cases columns
# ---------------------------------------------------------------------------

CLAIM_ROW = {
    "case_id": "C_TEST_001",
    "npi": "1234567890",
    "provider_name": "SMITH, JOHN M.D.",
    "state": "TX",
    "city": "HOUSTON",
    "hcpcs_cd": "99213",
    "hcpcs_desc": "OFFICE/OUTPATIENT VISIT EST",
    "place_of_service": "11",
    "provider_type": "Internal Medicine",
    "avg_submitted_charge": 150.0,
    "tot_srvcs": 200,
    "tot_benes": 50,
    "present_in_2025_enrollment_file": 1,
    "present_in_2026_revocation_file": 0,
    "medicare_participating_ind": "Y",
    "provider_total_benes": 200.0,
    "peer_scope": "Internal Medicine|99213",
    "peer_case_count": 100,
    "peer_avg_tot_srvcs": 120.0,
    "service_volume_peer_z": 1.5,
    "services_per_bene_peer_z": 0.8,
    "submitted_to_allowed_peer_z": 0.5,
    "payment_peer_z": 0.3,
    "top_code_share": 0.4,
    "service_hhi": 0.2,
}


# ---------------------------------------------------------------------------
# Mock DB connection
# ---------------------------------------------------------------------------


class FakeCursor:
    """Minimal async cursor that returns CLAIM_ROW then None for features."""

    def __init__(self, row):
        self._row = row
        self._call_count = 0

    async def execute(self, sql, params=None):
        self._call_count += 1

    async def fetchone(self):
        # First call: random claim. Second call: features (return None).
        if self._call_count <= 1:
            return self._row
        return None


class FakeConn:
    def __init__(self, row):
        self._row = row

    @asynccontextmanager
    async def cursor(self, row_factory=None):
        yield FakeCursor(self._row)


class FakePool:
    """Minimal async pool that returns a FakeConn."""

    def __init__(self, row=CLAIM_ROW):
        self._row = row

    @asynccontextmanager
    async def connection(self):
        yield FakeConn(self._row)


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(router, prefix="/api")
    return _app


@pytest.fixture(autouse=True)
def _mock_pool():
    with patch("src.api.routes.live._pool", FakePool()):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_returns_sse_content_type(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream("GET", "/api/live/stream?limit=1&interval=0.5") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_stream_returns_valid_json_events(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream("GET", "/api/live/stream?limit=2&interval=0.5") as resp:
            events = []
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    events.append(payload)

            assert len(events) == 2


@pytest.mark.asyncio
async def test_event_has_required_fields(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream("GET", "/api/live/stream?limit=1&interval=0.5") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    required = {
                        "event_id",
                        "timestamp",
                        "npi",
                        "provider_name",
                        "state",
                        "city",
                        "hcpcs_code",
                        "submitted_charge",
                        "risk_score",
                        "legitimacy_score",
                        "case_label",
                        "signals",
                        "scoring_latency_ms",
                    }
                    assert required.issubset(event.keys()), (
                        f"Missing fields: {required - event.keys()}"
                    )
                    break


@pytest.mark.asyncio
async def test_event_scores_are_valid(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream("GET", "/api/live/stream?limit=1&interval=0.5") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    assert 0 <= event["risk_score"] <= 100
                    assert 0 <= event["legitimacy_score"] <= 100
                    assert event["case_label"] in ("high_risk", "review", "stable")
                    assert event["scoring_latency_ms"] >= 0
                    break


@pytest.mark.asyncio
async def test_limit_parameter_stops_stream(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream("GET", "/api/live/stream?limit=3&interval=0.5") as resp:
            count = 0
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    count += 1
            assert count == 3
