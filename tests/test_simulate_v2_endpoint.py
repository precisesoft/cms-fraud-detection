"""Tests for POST /api/v2/claims/simulate — route-level with mocked DB and AI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.simulate_v2 import router

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


class _Cursor:
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


class _Conn:
    def __init__(
        self,
        provider: dict | None = PROVIDER_ROW,
        peers: dict | None = PEER_ROW,
        features: dict | None = None,
    ):
        self._results = [provider, peers, features]

    def cursor(self, row_factory=None):
        return _Cursor(self._results)


def _make_app(
    provider: dict | None = PROVIDER_ROW,
    peers: dict | None = PEER_ROW,
    features: dict | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    app = FastAPI(lifespan=_noop_lifespan)
    app.include_router(router, prefix="/api")

    conn = _Conn(provider, peers, features)

    async def fake_db():
        yield conn

    app.dependency_overrides[get_db] = fake_db
    return app


VALID_REQUEST = {
    "npi": "1234567890",
    "hcpcs_cd": "99213",
    "submitted_charge": 200.0,
    "num_services": 500,
    "num_benes": 100,
}


@pytest.mark.anyio
@patch("src.api.routes.simulate_v2.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_v2_returns_ml_probability(mock_narrative: AsyncMock):
    app = _make_app(features=FEATURES_ROW)
    with (
        patch("src.api.routes.simulate_v2.score_provider", return_value=0.77),
        patch("src.api.routes.simulate_v2.score_observation", return_value=64.2),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v2/claims/simulate", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["anomaly_score"] == 0.77
    assert body["ml_predicted_probability"] == 64.2


@pytest.mark.anyio
@patch("src.api.routes.simulate_v2.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_simulate_v2_keeps_legacy_fields(mock_narrative: AsyncMock):
    app = _make_app(features=None)
    with patch("src.api.routes.simulate_v2.score_observation", return_value=None):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v2/claims/simulate", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["npi"] == VALID_REQUEST["npi"]
    assert body["hcpcs_cd"] == VALID_REQUEST["hcpcs_cd"]
    assert "risk_score" in body
    assert "risk_band" in body
    assert "recommendation" in body
    assert body["ml_predicted_probability"] is None
