"""Tests for POST /api/v2/score — hybrid scoring endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.score_v2 import router

ENROLLED_PROVIDER = {
    "present_in_2025_enrollment_file": 1,
    "present_in_2026_revocation_file": 0,
    "medicare_participating_ind": "Y",
    "provider_type": "Internal Medicine",
    "provider_total_benes": 200.0,
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
    "avg_services_per_bene": 2.0,
    "mean_payment_ratio": 0.5,
    "provider_total_payment_amt": 200000.0,
    "unique_hcpcs_codes": 3,
    "unique_place_of_service": 2,
}


class _ScoreCursor:
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
    def __init__(
        self,
        provider: dict | None,
        peers: dict | None = None,
        features: dict | None = None,
    ):
        self._queue: list[dict | None] = [provider, peers, features]

    def cursor(self, row_factory=None):
        result = self._queue.pop(0) if self._queue else None
        return _ScoreCursor([result])


def _make_app(
    provider: dict | None,
    peers: dict | None = None,
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


@pytest.mark.anyio
@patch("src.api.routes.score_v2.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_score_v2_returns_ml_and_composite_fields(mock_narrative: AsyncMock):
    app = _make_app(ENROLLED_PROVIDER, PEER_STATS_NORMAL, FEATURES_ROW)
    with (
        patch("src.api.routes.score_v2.score_provider", return_value=22.5),
        patch("src.api.routes.score_v2.score_observation", return_value=64.2),
        patch("src.api.routes.score_v2.compute_composite_score", return_value=(68.5, "high")),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v2/score",
                json={
                    "npi": "1234567890",
                    "hcpcs_cd": "99213",
                    "tot_srvcs": 120.0,
                    "avg_submitted_charge": 200.0,
                },
            )

    assert response.status_code == 200
    body = response.json()
    assert body["anomaly_score"] == 22.5
    assert body["ml_predicted_probability"] == 64.2
    assert body["composite_score"] == 68.5
    assert body["composite_risk_label"] == "high"
    assert "risk_score" in body
    assert "legitimacy_score" in body


@pytest.mark.anyio
@patch("src.api.routes.score_v2.generate_narrative", new_callable=AsyncMock, return_value=None)
async def test_score_v2_keeps_working_without_ml_bundle(mock_narrative: AsyncMock):
    app = _make_app(ENROLLED_PROVIDER, None, None)
    with (
        patch("src.api.routes.score_v2.score_observation", return_value=None),
        patch("src.api.routes.score_v2.compute_composite_score", return_value=(12.0, "low")),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v2/score", json={"npi": "1234567890"})

    assert response.status_code == 200
    body = response.json()
    assert body["ml_predicted_probability"] is None
    assert body["composite_score"] == 12.0
    assert body["composite_risk_label"] == "low"
    assert body["anomaly_score"] is None


@pytest.mark.anyio
async def test_score_v2_unknown_npi_returns_404():
    app = _make_app(None, None, None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v2/score", json={"npi": "0000000000"})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
