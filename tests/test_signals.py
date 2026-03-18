"""Tests for GET /api/providers/{npi}/signals and /api/providers/{npi}/peers."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.signals import router

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

# Row that triggers enrollment + peer risk signals
CASE_ROW_HIGH_RISK = {
    "present_in_2025_enrollment_file": False,
    "present_in_2026_revocation_file": True,
    "medicare_participating_ind": "N",
    "provider_total_benes": 500,
    "peer_case_count": 30,
    "peer_avg_tot_srvcs": 100.0,
    "service_volume_peer_z": 3.5,
    "services_per_bene_peer_z": 2.8,
    "submitted_to_allowed_peer_z": 1.5,
    "payment_peer_z": 0.5,
    "hcpcs_cd": "99213",
    "hcpcs_desc": "Office/outpatient visit est",
    "seed_risk_score": 72,
    "seed_legitimacy_score": 25,
}

# Row with peer-aligned z-scores (triggers legitimacy signals)
CASE_ROW_STABLE = {
    "present_in_2025_enrollment_file": True,
    "present_in_2026_revocation_file": False,
    "medicare_participating_ind": "Y",
    "provider_total_benes": 50,
    "peer_case_count": 40,
    "peer_avg_tot_srvcs": 80.0,
    "service_volume_peer_z": 0.3,
    "services_per_bene_peer_z": 0.2,
    "submitted_to_allowed_peer_z": 0.1,
    "payment_peer_z": 0.4,
    "hcpcs_cd": "99214",
    "hcpcs_desc": "Office/outpatient visit est, moderate",
    "seed_risk_score": 15,
    "seed_legitimacy_score": 80,
}

# Peer comparison row
PEER_ROW = {
    "hcpcs_cd": "99213",
    "hcpcs_desc": "Office/outpatient visit est",
    "tot_srvcs": 200.0,
    "peer_avg_tot_srvcs": 100.0,
    "service_volume_peer_z": 3.5,
    "services_per_bene": 4.0,
    "services_per_bene_peer_z": 2.8,
    "submitted_to_allowed_ratio": 1.5,
    "submitted_to_allowed_peer_z": 1.5,
    "avg_medicare_payment_amt": 65.0,
    "payment_peer_z": 0.5,
    "peer_scope": "state_specific",
    "peer_case_count": 30,
    "seed_risk_score": 72,
    "seed_case_label": "high_risk",
}


class _FakeCursor:
    """Single-query cursor returning configurable rows."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    async def execute(self, sql: str, params: list | None = None):
        pass

    async def fetchall(self) -> list[dict]:
        return self._rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _FakeConn:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def cursor(self, row_factory=None):
        return _FakeCursor(self._rows)


def _make_app(rows: list[dict]) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(rows)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Tests — signals endpoint
# ---------------------------------------------------------------------------


class TestGetProviderSignals:
    async def test_returns_signals(self):
        app = _make_app([CASE_ROW_HIGH_RISK])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/signals")

        assert resp.status_code == 200
        signals = resp.json()
        assert len(signals) > 0
        assert all("name" in s for s in signals)
        assert all("direction" in s for s in signals)

    async def test_404_when_no_cases(self):
        app = _make_app([])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/0000000000/signals")

        assert resp.status_code == 404
        assert "No cases found" in resp.json()["detail"]

    async def test_deduplicates_signals(self):
        """Two rows with the same signal should produce only one entry."""
        row2 = {**CASE_ROW_HIGH_RISK, "hcpcs_cd": "99214"}
        app = _make_app([CASE_ROW_HIGH_RISK, row2])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/signals")

        signals = resp.json()
        keys = [(s["name"], s["direction"]) for s in signals]
        assert len(keys) == len(set(keys)), "Duplicate signals found"

    async def test_risk_signals_sorted_first(self):
        app = _make_app([CASE_ROW_STABLE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/signals")

        signals = resp.json()
        directions = [s["direction"] for s in signals]
        # Risk signals come before legitimacy in the sorted order
        risk_done = False
        for d in directions:
            if d == "legitimacy":
                risk_done = True
            if d == "risk" and risk_done:
                raise AssertionError("Risk signal found after legitimacy signals")

    async def test_signal_structure(self):
        app = _make_app([CASE_ROW_HIGH_RISK])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/signals")

        signal = resp.json()[0]
        assert "name" in signal
        assert "category" in signal
        assert "direction" in signal
        assert "description" in signal
        assert "threshold" in signal

    async def test_enrollment_signals_fire(self):
        """Revoked + not-enrolled row should produce those risk signals."""
        app = _make_app([CASE_ROW_HIGH_RISK])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/signals")

        names = [s["name"] for s in resp.json()]
        assert "revoked_provider" in names
        assert "not_in_current_enrollment_file" in names

    async def test_legitimacy_signals_fire(self):
        """Enrolled + participating + peer-aligned row should produce legitimacy signals."""
        app = _make_app([CASE_ROW_STABLE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/signals")

        names = [s["name"] for s in resp.json()]
        assert "present_in_current_enrollment_file" in names
        assert "no_revocation_match" in names
        assert "medicare_participating" in names


# ---------------------------------------------------------------------------
# Tests — peers endpoint
# ---------------------------------------------------------------------------


class TestGetProviderPeers:
    async def test_returns_peer_data(self):
        app = _make_app([PEER_ROW])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/peers")

        assert resp.status_code == 200
        body = resp.json()
        assert body["npi"] == "1234567890"
        assert body["total_lines"] == 1
        assert len(body["lines"]) == 1

    async def test_404_when_no_cases(self):
        app = _make_app([])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/0000000000/peers")

        assert resp.status_code == 404
        assert "No cases found" in resp.json()["detail"]

    async def test_peer_line_structure(self):
        app = _make_app([PEER_ROW])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/peers")

        line = resp.json()["lines"][0]
        assert line["hcpcs_cd"] == "99213"
        assert line["tot_srvcs"] == 200.0
        assert line["peer_avg_tot_srvcs"] == 100.0
        assert line["service_volume_peer_z"] == 3.5
        assert line["peer_scope"] == "state_specific"
        assert line["seed_risk_score"] == 72
        assert line["seed_case_label"] == "high_risk"

    async def test_multiple_lines(self):
        row2 = {**PEER_ROW, "hcpcs_cd": "99214", "hcpcs_desc": "Office visit moderate"}
        app = _make_app([PEER_ROW, row2])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/peers")

        body = resp.json()
        assert body["total_lines"] == 2
        assert len(body["lines"]) == 2
        codes = [line["hcpcs_cd"] for line in body["lines"]]
        assert "99213" in codes
        assert "99214" in codes
