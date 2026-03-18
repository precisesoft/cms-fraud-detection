"""Tests for GET /api/dashboard and GET /api/dashboard/heatmap."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.dashboard import router

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

COUNTS_ROW = {"total_providers": 500, "total_cases": 5000}

DIST_ROW = {"high_risk": 50, "review": 150, "stable": 300}

TOP_ROWS = [
    {
        "npi": "1111111111",
        "provider_name": "HIGH RISK MEDICAL",
        "provider_type": "Internal Medicine",
        "state": "CA",
        "city": "Los Angeles",
        "entity_code": "I",
        "max_seed_risk_score": 85,
        "service_line_count": 20,
        "total_estimated_payment": 100000.0,
        "revoked_2026": 1,
    },
    {
        "npi": "2222222222",
        "provider_name": "MODERATE CLINIC",
        "provider_type": "Cardiology",
        "state": "NY",
        "city": "New York",
        "entity_code": "I",
        "max_seed_risk_score": 72,
        "service_line_count": 10,
        "total_estimated_payment": 50000.0,
        "revoked_2026": 0,
    },
]

HEATMAP_ROWS = [
    {"state": "CA", "provider_count": 200, "avg_risk_score": 42.5, "flagged_count": 30},
    {"state": "NY", "provider_count": 150, "avg_risk_score": 38.2, "flagged_count": 18},
    {"state": "TX", "provider_count": 100, "avg_risk_score": 35.1, "flagged_count": 10},
]


class _DashboardCursor:
    """Multi-query cursor: counts → distribution → top providers."""

    def __init__(self, counts: dict, dist: dict, top: list[dict]):
        self._results: list = [counts, dist, top]
        self._call = 0

    async def execute(self, sql: str, params: list | None = None):
        self._call += 1

    async def fetchone(self) -> dict | None:
        return self._results[self._call - 1]

    async def fetchall(self) -> list[dict]:
        return self._results[self._call - 1]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _HeatmapCursor:
    """Single-query cursor for heatmap."""

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
    def __init__(
        self,
        *,
        counts: dict = COUNTS_ROW,
        dist: dict = DIST_ROW,
        top: list[dict] = TOP_ROWS,
        heatmap: list[dict] = HEATMAP_ROWS,
        mode: str = "dashboard",
    ):
        self._counts = counts
        self._dist = dist
        self._top = top
        self._heatmap = heatmap
        self._mode = mode

    def cursor(self, row_factory=None):
        if self._mode == "heatmap":
            return _HeatmapCursor(self._heatmap)
        return _DashboardCursor(self._counts, self._dist, self._top)


def _make_app(mode: str = "dashboard", **kwargs) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(mode=mode, **kwargs)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Tests — dashboard endpoint
# ---------------------------------------------------------------------------


class TestDashboard:
    async def test_returns_200(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard")

        assert resp.status_code == 200

    async def test_response_structure(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard")

        body = resp.json()
        assert "total_providers" in body
        assert "total_cases" in body
        assert "risk_distribution" in body
        assert "top_providers" in body

    async def test_counts(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard")

        body = resp.json()
        assert body["total_providers"] == 500
        assert body["total_cases"] == 5000

    async def test_risk_distribution(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard")

        dist = resp.json()["risk_distribution"]
        assert dist["high_risk"] == 50
        assert dist["review"] == 150
        assert dist["stable"] == 300

    async def test_top_providers(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard")

        top = resp.json()["top_providers"]
        assert len(top) == 2
        assert top[0]["npi"] == "1111111111"
        assert top[0]["risk_band"] == "high_risk"
        assert top[1]["risk_band"] == "high_risk"

    async def test_empty_data(self):
        app = _make_app(
            counts={"total_providers": 0, "total_cases": 0},
            dist={"high_risk": 0, "review": 0, "stable": 0},
            top=[],
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard")

        body = resp.json()
        assert body["total_providers"] == 0
        assert body["total_cases"] == 0
        assert body["top_providers"] == []


# ---------------------------------------------------------------------------
# Tests — heatmap endpoint
# ---------------------------------------------------------------------------


class TestHeatmap:
    async def test_returns_200(self):
        app = _make_app(mode="heatmap")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard/heatmap")

        assert resp.status_code == 200

    async def test_response_structure(self):
        app = _make_app(mode="heatmap")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard/heatmap")

        body = resp.json()
        assert "data" in body
        assert len(body["data"]) == 3

    async def test_heatmap_entries(self):
        app = _make_app(mode="heatmap")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard/heatmap")

        entry = resp.json()["data"][0]
        assert entry["state"] == "CA"
        assert entry["provider_count"] == 200
        assert entry["avg_risk_score"] == 42.5
        assert entry["flagged_count"] == 30

    async def test_empty_heatmap(self):
        app = _make_app(mode="heatmap", heatmap=[])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard/heatmap")

        assert resp.json()["data"] == []

    async def test_all_states_present(self):
        app = _make_app(mode="heatmap")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard/heatmap")

        states = [entry["state"] for entry in resp.json()["data"]]
        assert "CA" in states
        assert "NY" in states
        assert "TX" in states
