"""Tests for POST /api/score — on-the-fly scoring endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.score import router

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

ENROLLED_PROVIDER = {
    "present_in_2025_enrollment_file": 1,
    "present_in_2026_revocation_file": 0,
    "medicare_participating_ind": "Y",
    "provider_type": "Internal Medicine",
    "provider_total_benes": 200.0,
    "provider_name": "SMITH JOHN MD",
    "state": "CA",
}

REVOKED_PROVIDER = {
    "present_in_2025_enrollment_file": 0,
    "present_in_2026_revocation_file": 1,
    "medicare_participating_ind": "N",
    "provider_type": "Internal Medicine",
    "provider_total_benes": 30.0,
    "provider_name": "DOE JANE MD",
    "state": "TX",
}

PEER_STATS_NORMAL = {
    "peer_count": 50,
    "avg_srvcs": 100.0,
    "std_srvcs": 20.0,
    "avg_spb": 5.0,
    "std_spb": 1.0,
    "avg_ratio": 1.2,
    "std_ratio": 0.3,
    "avg_payment": 80.0,
    "std_payment": 15.0,
    "avg_charge": 120.0,
    "std_charge": 25.0,
}

PEER_STATS_TOO_FEW = {**PEER_STATS_NORMAL, "peer_count": 5}


class _ScoreCursor:
    """Cursor that returns results from a shared queue."""

    def __init__(self, results: list[dict | None]):
        self._results = results

    async def execute(self, sql: str, params: list | None = None):
        pass

    async def fetchone(self) -> dict | None:
        return self._results.pop(0) if self._results else None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _FakeConn:
    """Fake connection that returns provider on first cursor, peers on second."""

    def __init__(self, provider: dict | None, peers: dict | None = None):
        self._queue: list[dict | None] = [provider]
        if peers is not None:
            self._queue.append(peers)

    def cursor(self, row_factory=None):
        result = self._queue.pop(0) if self._queue else None
        return _ScoreCursor([result])


def _make_app(provider: dict | None, peers: dict | None = None) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(provider, peers)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Tests — provider not found
# ---------------------------------------------------------------------------


class TestProviderNotFound:
    async def test_unknown_npi_returns_404(self):
        app = _make_app(provider=None)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/score", json={"npi": "0000000000"})

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests — NPI-only scoring (no HCPCS)
# ---------------------------------------------------------------------------


class TestNpiOnlyScoring:
    async def test_enrolled_provider_npi_only(self):
        """Without HCPCS, only enrollment signals fire."""
        app = _make_app(provider=ENROLLED_PROVIDER)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/score", json={"npi": "1234567890"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["npi"] == "1234567890"
        # Enrolled + no revocation + participating + large panel
        assert body["legitimacy_score"] > 0
        assert body["risk_score"] == 0
        assert body["risk_band"] == "stable"

    async def test_revoked_provider_npi_only(self):
        app = _make_app(provider=REVOKED_PROVIDER)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/score", json={"npi": "9999999999"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["risk_score"] > 0
        assert body["risk_band"] in ("review", "high_risk")


# ---------------------------------------------------------------------------
# Tests — scoring with HCPCS and peer baselines
# ---------------------------------------------------------------------------


class TestScoringWithPeers:
    async def test_normal_volume_no_risk(self):
        """tot_srvcs near the peer average → no volume outlier."""
        app = _make_app(provider=ENROLLED_PROVIDER, peers=PEER_STATS_NORMAL)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/score",
                json={"npi": "1234567890", "hcpcs_cd": "99213", "tot_srvcs": 110.0},
            )

        body = resp.json()
        assert body["risk_score"] == 0
        assert body["risk_band"] == "stable"

    async def test_extreme_volume_fires_risk(self):
        """tot_srvcs far above peer average → volume outlier signal fires."""
        app = _make_app(provider=ENROLLED_PROVIDER, peers=PEER_STATS_NORMAL)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # z = (500 - 100) / 20 = 20.0 → extreme outlier
            resp = await client.post(
                "/api/score",
                json={"npi": "1234567890", "hcpcs_cd": "99213", "tot_srvcs": 500.0},
            )

        body = resp.json()
        assert body["risk_score"] > 0
        signal_names = [s["name"] for s in body["signals"]]
        assert "service_volume_outlier" in signal_names

    async def test_too_few_peers_skips_z_scores(self):
        """When peer count < MIN_PEER_COUNT, z-score signals don't fire."""
        app = _make_app(provider=ENROLLED_PROVIDER, peers=PEER_STATS_TOO_FEW)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/score",
                json={"npi": "1234567890", "hcpcs_cd": "99213", "tot_srvcs": 500.0},
            )

        body = resp.json()
        # No volume outlier because peers < MIN_PEER_COUNT
        signal_names = [s["name"] for s in body["signals"]]
        assert "service_volume_outlier" not in signal_names


# ---------------------------------------------------------------------------
# Tests — response structure
# ---------------------------------------------------------------------------


class TestScoreResponseStructure:
    async def test_response_has_required_fields(self):
        app = _make_app(provider=ENROLLED_PROVIDER)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/score", json={"npi": "1234567890"})

        body = resp.json()
        assert "npi" in body
        assert "risk_score" in body
        assert "legitimacy_score" in body
        assert "risk_band" in body
        assert "signals" in body
        assert isinstance(body["signals"], list)

    async def test_signal_structure(self):
        app = _make_app(provider=ENROLLED_PROVIDER)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/score", json={"npi": "1234567890"})

        body = resp.json()
        assert len(body["signals"]) > 0
        sig = body["signals"][0]
        assert "name" in sig
        assert "category" in sig
        assert "direction" in sig
        assert "description" in sig

    async def test_scores_within_bounds(self):
        app = _make_app(provider=REVOKED_PROVIDER, peers=PEER_STATS_NORMAL)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/score",
                json={"npi": "9999999999", "hcpcs_cd": "99213", "tot_srvcs": 500.0},
            )

        body = resp.json()
        assert 0 <= body["risk_score"] <= 100
        assert 0 <= body["legitimacy_score"] <= 100
        assert body["risk_band"] in ("stable", "review", "high_risk")

    async def test_request_validation_missing_npi(self):
        app = _make_app(provider=ENROLLED_PROVIDER)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/score", json={})

        assert resp.status_code == 422
