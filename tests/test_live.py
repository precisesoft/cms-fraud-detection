"""Tests for the persistent live monitor — queue manager + SSE broadcast."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.live_queue import QueueEvent, QueueManager
from src.api.routes.live import router

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_EVENT = QueueEvent(
    npi="1234567890",
    provider_name="SMITH, JOHN M.D.",
    state="TX",
    city="HOUSTON",
    hcpcs_code="99213",
    hcpcs_desc="OFFICE/OUTPATIENT VISIT EST",
    submitted_charge=150.0,
    provider_type="Internal Medicine",
    risk_score=35,
    legitimacy_score=55,
    case_label="review",
    anomaly_score=None,
    signals=["service_volume_outlier"],
    scoring_latency_ms=1.2,
)


@pytest.fixture
def queue_mgr():
    """A QueueManager pre-loaded with a small test queue."""
    mgr = QueueManager()
    mgr.queue = [SAMPLE_EVENT] * 5
    mgr.ready = True
    mgr.running = True
    mgr.queue_actual_counts = {
        "high_risk": 0,
        "review": 5,
        "stable": 0,
        "total": 5,
    }
    return mgr


@pytest.fixture
def app(queue_mgr):
    _app = FastAPI()
    _app.include_router(router, prefix="/api")
    return _app


# ---------------------------------------------------------------------------
# QueueManager unit tests
# ---------------------------------------------------------------------------


class TestQueueManager:
    def test_subscribe_and_unsubscribe(self, queue_mgr: QueueManager):
        q = queue_mgr.subscribe()
        assert len(queue_mgr._subscribers) == 1
        queue_mgr.unsubscribe(q)
        assert len(queue_mgr._subscribers) == 0

    def test_unsubscribe_nonexistent(self, queue_mgr: QueueManager):
        import asyncio

        q: asyncio.Queue[str] = asyncio.Queue()
        queue_mgr.unsubscribe(q)  # should not raise

    def test_status(self, queue_mgr: QueueManager):
        status = queue_mgr.status()
        assert status["running"] is True
        assert status["ready"] is True
        assert status["queue_size"] == 5
        assert status["distribution"]["total"] == 5

    def test_set_tps_clamps(self, queue_mgr: QueueManager):
        queue_mgr.set_tps(0.01)
        assert queue_mgr.tps == 0.1
        queue_mgr.set_tps(50.0)
        assert queue_mgr.tps == 20.0
        queue_mgr.set_tps(5.0)
        assert queue_mgr.tps == 5.0

    def test_diverse_sample_returns_up_to_target(self):
        events = [
            QueueEvent(
                npi=f"NPI{i}",
                provider_name=f"Dr {i}",
                state="TX" if i % 2 == 0 else "CA",
                city="City",
                hcpcs_code="99213",
                hcpcs_desc="Visit",
                submitted_charge=100.0,
                provider_type="Internal Medicine",
                risk_score=50,
                legitimacy_score=50,
                case_label="review",
                anomaly_score=None,
                signals=[],
                scoring_latency_ms=1.0,
            )
            for i in range(20)
        ]
        result = QueueManager._diverse_sample(events, 10)
        assert len(result) == 10

    def test_diverse_sample_returns_all_if_under_target(self):
        events = [SAMPLE_EVENT]
        result = QueueManager._diverse_sample(events, 100)
        assert len(result) == 1

    def test_interleave_produces_correct_length(self):
        hr = [SAMPLE_EVENT] * 3
        rv = [SAMPLE_EVENT] * 7
        st = [SAMPLE_EVENT] * 10
        result = QueueManager._interleave(hr, rv, st)
        assert len(result) == 20

    @pytest.mark.asyncio
    async def test_broadcast_to_subscribers(self, queue_mgr: QueueManager):
        q1 = queue_mgr.subscribe()
        q2 = queue_mgr.subscribe()
        await queue_mgr._broadcast("data: test\n\n")
        assert await q1.get() == "data: test\n\n"
        assert await q2.get() == "data: test\n\n"


# ---------------------------------------------------------------------------
# SSE endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_endpoint(app, queue_mgr):
    with patch("src.api.routes.live.queue_manager", queue_mgr):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/live/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["running"] is True
            assert data["queue_size"] == 5


@pytest.mark.asyncio
async def test_tps_endpoint(app, queue_mgr):
    with patch("src.api.routes.live.queue_manager", queue_mgr):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/live/tps?tps=5.0")
            assert resp.status_code == 200
            assert resp.json()["tps"] == 5.0


@pytest.mark.asyncio
async def test_stream_returns_sse_content_type(app, queue_mgr):
    with patch("src.api.routes.live.queue_manager", queue_mgr):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            async with client.stream("GET", "/api/live/stream") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]
