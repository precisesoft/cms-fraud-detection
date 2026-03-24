"""Tests for GET /api/providers/{npi}/score-details."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.providers import router

PROVIDER_ROW = {
    "npi": "1234567890",
    "max_seed_risk_score": 72,
    "provider_total_payment_amt": 50000.0,
    "unique_hcpcs_codes": 8,
    "unique_place_of_service": 2,
    "mean_volume_z": 1.5,
    "mean_intensity_z": 0.9,
    "mean_charge_z": 1.2,
    "mean_payment_z": 0.7,
    "service_hhi": 0.25,
    "top_code_share": 0.4,
    "provider_total_benes": 100.0,
}

LATEST_MODEL = {"model_name": "weak_supervised_k8s_model", "model_version": "v1"}
AGG_ROW = {
    "service_line_scored_count": 4,
    "ml_suspicion_max": 81.2,
    "ml_suspicion_avg": 55.0,
    "hybrid_composite_max": 76.3,
    "hybrid_composite_avg": 50.1,
}


class _Cursor:
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


class _Conn:
    def __init__(self, provider: dict | None, latest_model: dict | None, aggregate: dict | None):
        self._results = [provider, latest_model, aggregate]

    def cursor(self, row_factory=None):
        result = self._results.pop(0) if self._results else None
        return _Cursor([result])


def _make_app(provider: dict | None, latest_model: dict | None, aggregate: dict | None) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    app = FastAPI(lifespan=_noop_lifespan)
    app.include_router(router, prefix="/api")
    conn = _Conn(provider, latest_model, aggregate)

    async def fake_db():
        yield conn

    app.dependency_overrides[get_db] = fake_db
    return app


async def test_provider_score_details_returns_hybrid_summary():
    app = _make_app(PROVIDER_ROW, LATEST_MODEL, AGG_ROW)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/providers/1234567890/score-details")

    assert response.status_code == 200
    body = response.json()
    assert body["explainable_risk_score"] == 72
    assert body["ml_suspicion_max"] == 81.2
    assert body["hybrid_composite_max"] == 76.3
    assert body["hybrid_risk_label"] == "high"


async def test_provider_score_details_returns_404_when_missing():
    app = _make_app(None, None, None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/providers/1234567890/score-details")

    assert response.status_code == 404
