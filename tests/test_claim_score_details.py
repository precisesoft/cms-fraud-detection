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


# ---------- _hybrid_label_from_score fallback coverage ----------


async def test_hybrid_label_fallback_when_risk_label_is_none():
    """score_row exists but risk_label is falsy → _hybrid_label_from_score called."""
    score_row_no_label = {
        "predicted_probability": 55.0,
        "composite_score": 71.4,
        "risk_label": None,
        "model_name": "weak_supervised_k8s_model",
        "model_version": "v1",
    }
    app = _make_app(CLAIM_ROW, LATEST_MODEL, score_row_no_label)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/claims/1234567890-99213/score-details")

    assert resp.status_code == 200
    body = resp.json()
    # 71.4 >= 70 → "high"
    assert body["hybrid_risk_label"] == "high"
    assert body["hybrid_composite_score"] == 71.4


async def test_hybrid_label_critical_threshold():
    """composite_score >= 90 → critical."""
    score_row = {
        "predicted_probability": 95.0,
        "composite_score": 92.5,
        "risk_label": None,
        "model_name": "weak_supervised_k8s_model",
        "model_version": "v1",
    }
    app = _make_app(CLAIM_ROW, LATEST_MODEL, score_row)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/claims/1234567890-99213/score-details")

    assert resp.status_code == 200
    assert resp.json()["hybrid_risk_label"] == "critical"


async def test_hybrid_label_medium_threshold():
    """composite_score >= 40 and < 70 → medium."""
    score_row = {
        "predicted_probability": 40.0,
        "composite_score": 55.0,
        "risk_label": None,
        "model_name": "weak_supervised_k8s_model",
        "model_version": "v1",
    }
    app = _make_app(CLAIM_ROW, LATEST_MODEL, score_row)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/claims/1234567890-99213/score-details")

    assert resp.status_code == 200
    assert resp.json()["hybrid_risk_label"] == "medium"


async def test_hybrid_label_low_threshold():
    """composite_score < 40 → low."""
    score_row = {
        "predicted_probability": 10.0,
        "composite_score": 20.0,
        "risk_label": None,
        "model_name": "weak_supervised_k8s_model",
        "model_version": "v1",
    }
    app = _make_app(CLAIM_ROW, LATEST_MODEL, score_row)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/claims/1234567890-99213/score-details")

    assert resp.status_code == 200
    assert resp.json()["hybrid_risk_label"] == "low"


async def test_hybrid_label_none_when_no_score_row():
    """No score_row at all → hybrid_score is None → label is None."""
    app = _make_app(CLAIM_ROW, LATEST_MODEL, None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/claims/1234567890-99213/score-details")

    assert resp.status_code == 200
    body = resp.json()
    assert body["hybrid_risk_label"] is None
    assert body["hybrid_composite_score"] is None
    # model_name/model_version fall back to latest_model (lines 188-193)
    assert body["model_name"] == "weak_supervised_k8s_model"
    assert body["model_version"] == "v1"


async def test_model_fallback_when_score_row_lacks_model_fields():
    """score_row exists but model_name/model_version are None → fallback to latest_model."""
    score_row_no_model = {
        "predicted_probability": 50.0,
        "composite_score": 45.0,
        "risk_label": None,
        "model_name": None,
        "model_version": None,
    }
    app = _make_app(CLAIM_ROW, LATEST_MODEL, score_row_no_model)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/claims/1234567890-99213/score-details")

    assert resp.status_code == 200
    body = resp.json()
    # Falls back to latest_model for model_name/model_version (lines 188-193)
    assert body["model_name"] == "weak_supervised_k8s_model"
    assert body["model_version"] == "v1"
    # 45.0 >= 40 → medium
    assert body["hybrid_risk_label"] == "medium"
