"""Tests for GET /api/claims/{case_id}/score-details."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.claims import router

CLAIM_ROW = {
    "case_id": "1234567890-99213",
    "npi": "1234567890",
    "submitted_to_allowed_peer_z": 1.5,
    "services_per_bene": 6.0,
    "peer_avg_spb": 3.0,
    "seed_risk_score": 42,
}
LATEST_MODEL = {"model_name": "weak_supervised_k8s_model", "model_version": "v1"}
SCORE_ROW = {
    "predicted_probability": 64.2,
    "composite_score": 71.4,
    "risk_label": "high",
    "model_name": "weak_supervised_k8s_model",
    "model_version": "v1",
}


class _Cursor:
    def __init__(self, results: list[dict | None]):
        self._results = results

    async def execute(self, sql: str, params: tuple | list | None = None):
        pass

    async def fetchone(self) -> dict | None:
        return self._results.pop(0) if self._results else None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _Conn:
    def __init__(self, claim: dict | None, latest_model: dict | None, score_row: dict | None):
        self._results = [claim, latest_model, score_row]

    def cursor(self, row_factory=None):
        result = self._results.pop(0) if self._results else None
        return _Cursor([result])


def _make_app(claim: dict | None, latest_model: dict | None, score_row: dict | None) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    app = FastAPI(lifespan=_noop_lifespan)
    app.include_router(router, prefix="/api")
    conn = _Conn(claim, latest_model, score_row)

    async def fake_db():
        yield conn

    app.dependency_overrides[get_db] = fake_db
    return app


async def test_claim_score_details_returns_hybrid_summary():
    app = _make_app(CLAIM_ROW, LATEST_MODEL, SCORE_ROW)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/claims/1234567890-99213/score-details")

    assert response.status_code == 200
    body = response.json()
    assert body["explainable_risk_score"] == 42
    assert body["ml_predicted_probability"] == 64.2
    assert body["hybrid_composite_score"] == 71.4
    assert body["hybrid_risk_label"] == "high"


async def test_claim_score_details_returns_404_when_missing():
    app = _make_app(None, None, None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/claims/missing/score-details")

    assert response.status_code == 404
