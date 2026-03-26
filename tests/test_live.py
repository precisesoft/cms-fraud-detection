"""Tests for the persistent live monitor — queue manager + SSE broadcast."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.live_queue import QueueEvent, QueueManager
from src.api.routes.live import router, stream_claims

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

    def test_score_row_returns_queue_event(self):
        """_score_row produces a QueueEvent from a case dict."""
        row = {
            "npi": "1234567890",
            "provider_name": "SMITH, JOHN",
            "state": "TX",
            "city": "HOUSTON",
            "hcpcs_cd": "99213",
            "hcpcs_desc": "OFFICE VISIT",
            "avg_submitted_charge": 150.0,
            "provider_type": "Internal Medicine",
            "service_volume_peer_z": 3.0,
            "services_per_bene_peer_z": 1.0,
            "submitted_to_allowed_peer_z": 1.0,
            "payment_peer_z": 0.5,
            "present_in_2025_enrollment_file": 1,
            "present_in_2026_revocation_file": 0,
            "medicare_participating_ind": "Y",
            "tot_srvcs": 500,
            "tot_benes": 50,
            "provider_total_benes": 200,
        }
        features_cache: dict[str, dict | None] = {"1234567890": None}
        evt = QueueManager._score_row(row, features_cache)
        assert isinstance(evt, QueueEvent)
        assert evt.npi == "1234567890"
        assert evt.state == "TX"
        assert isinstance(evt.risk_score, int)
        assert evt.case_label in ("high_risk", "review", "stable")

    def test_score_all_partitions_by_label(self):
        """_score_all partitions candidates into label buckets."""
        candidates = [
            {
                "npi": f"NPI{i}",
                "provider_name": f"Dr {i}",
                "state": "TX",
                "city": "HOUSTON",
                "hcpcs_cd": "99213",
                "hcpcs_desc": "VISIT",
                "avg_submitted_charge": 100.0,
                "provider_type": "Internal Medicine",
                "service_volume_peer_z": 0.5,
                "services_per_bene_peer_z": 0.5,
                "submitted_to_allowed_peer_z": 0.5,
                "payment_peer_z": 0.5,
                "present_in_2025_enrollment_file": 1,
                "present_in_2026_revocation_file": 0,
                "medicare_participating_ind": "Y",
                "tot_srvcs": 100,
                "tot_benes": 20,
                "provider_total_benes": 50,
            }
            for i in range(5)
        ]
        features_cache: dict[str, dict | None] = {f"NPI{i}": None for i in range(5)}
        result = QueueManager._score_all(candidates, features_cache)
        # All events should be categorized into one of the label buckets
        total = sum(len(v) for v in result.values())
        assert total == 5
        for label in result:
            assert label in ("high_risk", "review", "stable")


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
        resp = await stream_claims(0.0)
        assert resp.media_type == "text/event-stream"
        assert resp.headers["Cache-Control"] == "no-cache"
        assert resp.headers["Connection"] == "keep-alive"
        assert resp.headers["X-Accel-Buffering"] == "no"
