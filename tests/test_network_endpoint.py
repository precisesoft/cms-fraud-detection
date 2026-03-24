"""Tests for GET /api/network/{npi} — route-level with mocked DB."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.network import router

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

PROVIDER_ROW = {
    "npi": "1234567890",
    "provider_name": "Acme Health",
    "provider_type": "Internal Medicine",
    "state": "FL",
    "zip5": "33101",
    "city": "Miami",
    "max_seed_risk_score": 65,
    "revoked_2026": 0,
}

SAME_ZIP_ROWS = [
    {
        "npi": "9999999999",
        "provider_name": "Bad Clinic",
        "provider_type": "Cardiology",
        "state": "FL",
        "zip5": "33101",
        "city": "Miami",
        "max_seed_risk_score": 78,
        "revoked_2026": 1,
    },
]

SAME_ORG_ROWS: list[dict] = []

ZIP_STATS_ROW = {
    "total_in_zip": 15,
    "high_risk_in_zip": 4,
    "revoked_in_zip": 2,
    "avg_risk_in_zip": 42.3,
}


class _NetworkCursor:
    """Returns canned results based on query call order:
    1. provider lookup (fetchone)
    2. same-zip flagged (fetchall)
    3. same-org flagged (fetchall)
    4. zip stats (fetchone)
    """

    def __init__(
        self,
        provider: dict | None,
        same_zip: list[dict],
        same_org: list[dict],
        zip_stats: dict | None,
    ):
        self._results: list = [provider, same_zip, same_org, zip_stats]
        self._call = 0

    async def execute(self, sql: str, params: dict | None = None):
        self._call += 1

    async def fetchone(self) -> dict | None:
        return self._results[self._call - 1]

    async def fetchall(self) -> list[dict]:
        return self._results[self._call - 1]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _FakeConn:
    def __init__(
        self,
        provider: dict | None = PROVIDER_ROW,
        same_zip: list[dict] | None = None,
        same_org: list[dict] | None = None,
        zip_stats: dict | None = ZIP_STATS_ROW,
    ):
        self._provider = provider
        self._same_zip = same_zip if same_zip is not None else SAME_ZIP_ROWS
        self._same_org = same_org if same_org is not None else SAME_ORG_ROWS
        self._zip_stats = zip_stats

    def cursor(self, row_factory=None):
        return _NetworkCursor(self._provider, self._same_zip, self._same_org, self._zip_stats)


def _make_app(
    provider: dict | None = PROVIDER_ROW,
    same_zip: list[dict] | None = None,
    same_org: list[dict] | None = None,
    zip_stats: dict | None = ZIP_STATS_ROW,
) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(provider, same_zip, same_org, zip_stats)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNetworkEndpoint:
    @pytest.mark.anyio
    async def test_returns_200(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_response_structure(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")
        body = resp.json()
        assert body["npi"] == "1234567890"
        assert body["zip5"] == "33101"
        assert "same_zip_flagged" in body
        assert "same_org_flagged" in body
        assert "zip_risk_summary" in body

    @pytest.mark.anyio
    async def test_same_zip_flagged_populated(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")
        body = resp.json()
        assert len(body["same_zip_flagged"]) == 1
        neighbor = body["same_zip_flagged"][0]
        assert neighbor["npi"] == "9999999999"
        assert neighbor["risk_score"] == 78
        assert neighbor["revoked"] is True

    @pytest.mark.anyio
    async def test_zip_risk_summary(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")
        body = resp.json()
        summary = body["zip_risk_summary"]
        assert summary["total_in_zip"] == 15
        assert summary["high_risk_in_zip"] == 4
        assert summary["revoked_in_zip"] == 2
        assert summary["avg_risk_in_zip"] == 42.3

    @pytest.mark.anyio
    async def test_unknown_provider_returns_empty(self):
        app = _make_app(provider=None)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/0000000000")
        body = resp.json()
        assert resp.status_code == 200
        assert body["same_zip_flagged"] == []
        assert body["same_org_flagged"] == []
        assert body["zip_risk_summary"] is None

    @pytest.mark.anyio
    async def test_no_flagged_neighbors(self):
        app = _make_app(same_zip=[], same_org=[])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")
        body = resp.json()
        assert body["same_zip_flagged"] == []
        assert body["same_org_flagged"] == []

    @pytest.mark.anyio
    async def test_same_org_flagged(self):
        org_neighbor = {
            "npi": "7777777777",
            "provider_name": "Acme Health",
            "provider_type": "Internal Medicine",
            "state": "FL",
            "zip5": "33102",
            "city": "Miami",
            "max_seed_risk_score": 55,
            "revoked_2026": 0,
        }
        app = _make_app(same_org=[org_neighbor])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")
        body = resp.json()
        assert len(body["same_org_flagged"]) == 1
        assert body["same_org_flagged"][0]["npi"] == "7777777777"

    @pytest.mark.anyio
    async def test_no_zip5_skips_same_zip_and_zip_stats(self):
        """Provider with no zip5 should skip same-zip query and return zip_risk_summary=None
        (covers the zip5 branch-miss on lines 93 and 105)."""
        provider_no_zip = {**PROVIDER_ROW, "zip5": None}

        class _NoZipCursor:
            """Only ever returns provider (call 1); further calls return empty."""

            def __init__(self, provider):
                self._provider = provider
                self._call = 0

            async def execute(self, sql: str, params=None):
                self._call += 1

            async def fetchone(self):
                if self._call == 1:
                    return self._provider
                return None

            async def fetchall(self):
                return []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        class _NoZipConn:
            def cursor(self, row_factory=None):
                return _NoZipCursor(provider_no_zip)

        @asynccontextmanager
        async def _noop_lifespan(app: FastAPI):
            yield

        test_app = FastAPI(lifespan=_noop_lifespan)
        test_app.include_router(router, prefix="/api")

        async def fake_db():
            yield _NoZipConn()

        test_app.dependency_overrides[get_db] = fake_db

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")

        body = resp.json()
        assert resp.status_code == 200
        assert body["zip5"] is None
        assert body["same_zip_flagged"] == []
        assert body["zip_risk_summary"] is None

    @pytest.mark.anyio
    async def test_no_org_name_skips_same_org_query(self):
        """Provider with no provider_name should skip the same-org query
        (covers the org_name branch-miss on line 99)."""
        provider_no_org = {**PROVIDER_ROW, "provider_name": None}

        class _NoOrgCursor:
            """Returns provider on call 1, same_zip on call 2, zip_stats on call 3."""

            def __init__(self):
                self._call = 0

            async def execute(self, sql: str, params=None):
                self._call += 1

            async def fetchone(self):
                if self._call == 1:
                    return provider_no_org
                if self._call == 3:
                    return ZIP_STATS_ROW
                return None

            async def fetchall(self):
                return []  # same-zip returns empty

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        class _NoOrgConn:
            def cursor(self, row_factory=None):
                return _NoOrgCursor()

        @asynccontextmanager
        async def _noop_lifespan(app: FastAPI):
            yield

        test_app = FastAPI(lifespan=_noop_lifespan)
        test_app.include_router(router, prefix="/api")

        async def fake_db():
            yield _NoOrgConn()

        test_app.dependency_overrides[get_db] = fake_db

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/network/1234567890")

        body = resp.json()
        assert resp.status_code == 200
        assert body["same_org_flagged"] == []
