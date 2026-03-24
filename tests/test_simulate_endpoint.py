"""Tests for POST /api/claims/simulate — route-level with mocked DB and AI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.simulate import _build_comparison, _z_score, router

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

PROVIDER_ROW = {
    "present_in_2025_enrollment_file": 1,
    "present_in_2026_revocation_file": 0,
    "medicare_participating_ind": "Y",
    "provider_type": "Internal Medicine",
    "provider_total_benes": 200.0,
    "provider_name": "Test Provider",
    "state": "FL",
}

PEER_ROW = {
    "peer_count": 50,
    "avg_srvcs": 100.0,
    "std_srvcs": 30.0,
    "avg_spb": 5.0,
    "std_spb": 1.5,
    "avg_ratio": 1.2,
    "std_ratio": 0.3,
    "avg_payment": 80.0,
    "std_payment": 20.0,
    "avg_charge": 150.0,
    "std_charge": 40.0,
}

FEATURES_ROW = {
    "mean_volume_z": 1.0,
    "mean_intensity_z": 0.5,
    "mean_charge_z": 0.8,
    "mean_payment_z": 0.3,
    "service_hhi": 0.2,
    "top_code_share": 0.4,
    "top3_code_share": 0.6,
    "n_volume_outlier_lines": 1,
    "n_intensity_outlier_lines": 0,
    "n_charge_outlier_lines": 0,
    "frac_volume_outlier_lines": 0.1,
    "charge_cv": 0.5,
    "risk_legitimacy_gap": 10,
    "max_seed_risk_score": 40,
}


class _SimulateCursor:
    """Returns canned results from a shared result queue.

    simulate.py opens two separate cursor contexts, so we pull from the
    shared list across cursor instances to maintain query order.
    """

    def __init__(self, results: list):
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
    """Fake connection with shared result queue across cursor() calls.

    Query order: 1. provider lookup (fetchone), 2. peer baselines (fetchone),
    3. features row (fetchone for anomaly scorer).
    Keep in sync with simulate.py:simulate_claim.
    """

    def __init__(
        self,
        provider: dict | None = PROVIDER_ROW,
        peers: dict | None = PEER_ROW,
        features: dict | None = None,
    ):
        self._results: list = [provider, peers]
        # Third cursor call is always present (features query)
        self._results.append(features)

    def cursor(self, row_factory=None):
        return _SimulateCursor(self._results)


def _make_app(
    provider: dict | None = PROVIDER_ROW,
    peers: dict | None = PEER_ROW,
    features: dict | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(provider, peers, features)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Unit tests for pure helper functions
# ---------------------------------------------------------------------------


class TestZScore:
    def test_normal(self):
        assert _z_score(10.0, 5.0, 2.5) == 2.0

    def test_zero_std(self):
        assert _z_score(10.0, 5.0, 0.0) is None

    def test_none_value(self):
        assert _z_score(None, 5.0, 2.5) is None

    def test_none_mean(self):
        assert _z_score(10.0, None, 2.5) is None

    def test_none_std(self):
        assert _z_score(10.0, 5.0, None) is None

    def test_negative_z(self):
        result = _z_score(2.0, 5.0, 1.0)
        assert result is not None
        assert result == -3.0


class TestBuildComparison:
    def test_normal(self):
        comp = _build_comparison("volume", 100.0, 50.0, 25.0, 30)
        assert comp is not None
        assert comp.metric == "volume"
        assert comp.provider_value == 100.0
        assert comp.peer_mean == 50.0
        assert comp.z_score == 2.0
        assert comp.peer_count == 30

    def test_none_mean_returns_none(self):
        assert _build_comparison("volume", 100.0, None, 25.0, 30) is None

    def test_zero_std(self):
        comp = _build_comparison("volume", 100.0, 50.0, 0.0, 30)
        assert comp is not None
        assert comp.z_score == 0.0  # z_score returns None → defaults to 0.0


VALID_REQUEST = {
    "npi": "1234567890",
    "hcpcs_cd": "99213",
    "submitted_charge": 200.0,
    "num_services": 500,
    "num_benes": 100,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_returns_200(mock_narrative: AsyncMock):
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    assert resp.status_code == 200


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_response_structure(mock_narrative: AsyncMock):
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    body = resp.json()
    assert body["npi"] == "1234567890"
    assert body["hcpcs_cd"] == "99213"
    assert "risk_score" in body
    assert "risk_band" in body
    assert "recommendation" in body
    assert "signals" in body
    assert "peer_comparisons" in body


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_has_peer_comparisons(mock_narrative: AsyncMock):
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    body = resp.json()
    assert len(body["peer_comparisons"]) > 0
    comp = body["peer_comparisons"][0]
    assert "metric" in comp
    assert "provider_value" in comp
    assert "peer_mean" in comp
    assert "z_score" in comp
    assert "peer_count" in comp


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_risk_band_valid(mock_narrative: AsyncMock):
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    body = resp.json()
    assert body["risk_band"] in ("stable", "review", "high_risk")


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_recommendation_matches_band(mock_narrative: AsyncMock):
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    body = resp.json()
    band_to_rec = {"stable": "approve", "review": "review", "high_risk": "deny"}
    assert body["recommendation"] == band_to_rec[body["risk_band"]]


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_unknown_provider_returns_404(mock_narrative: AsyncMock):
    app = _make_app(provider=None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_no_peers(mock_narrative: AsyncMock):
    """When no peer data exists, should still score (without peer comparisons)."""
    no_peers = {
        "peer_count": 0,
        "avg_srvcs": None,
        "std_srvcs": None,
        "avg_spb": None,
        "std_spb": None,
        "avg_ratio": None,
        "std_ratio": None,
        "avg_payment": None,
        "std_payment": None,
        "avg_charge": None,
        "std_charge": None,
    }
    app = _make_app(peers=no_peers)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    body = resp.json()
    assert resp.status_code == 200
    assert body["peer_comparisons"] == []


@pytest.mark.anyio
@patch(
    "src.api.routes.simulate.generate_narrative",
    new_callable=AsyncMock,
    return_value="This provider shows elevated billing.",
)
async def test_simulate_narrative_included(mock_narrative: AsyncMock):
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    body = resp.json()
    assert body["narrative"] == "This provider shows elevated billing."
    mock_narrative.assert_awaited_once()


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_provider_metadata(mock_narrative: AsyncMock):
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    body = resp.json()
    assert body["provider_name"] == "Test Provider"
    assert body["provider_type"] == "Internal Medicine"
    assert body["state"] == "FL"


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_outlier_claim_gets_high_risk(mock_narrative: AsyncMock):
    """A claim with extreme volume should produce elevated risk."""
    outlier_request = {
        "npi": "1234567890",
        "hcpcs_cd": "99213",
        "submitted_charge": 200.0,
        "num_services": 5000,  # 50x peer average
        "num_benes": 10,
    }
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=outlier_request)
    body = resp.json()
    # With z-score > 100 on volume, this should flag
    assert body["risk_score"] > 0
    assert len(body["signals"]) > 0


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_validation_rejects_bad_input(mock_narrative: AsyncMock):
    """Missing required fields should return 422."""
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json={"npi": "123"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Anomaly score path (line 202: features_row is not None)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_anomaly_score_computed_when_features_present(mock_narrative: AsyncMock):
    """When the third DB cursor returns a features row, score_provider is called
    and anomaly_score is a float (covers line 202)."""
    app = _make_app(features=FEATURES_ROW)
    with patch("src.api.routes.simulate.score_provider", return_value=0.77):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    assert resp.status_code == 200
    assert resp.json()["anomaly_score"] == 0.77


@pytest.mark.anyio
@patch("src.api.routes.simulate.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_anomaly_score_none_when_no_features(mock_narrative: AsyncMock):
    """When the features query returns None, anomaly_score is null."""
    app = _make_app(features=None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/claims/simulate", json=VALID_REQUEST)
    assert resp.status_code == 200
    assert resp.json()["anomaly_score"] is None
