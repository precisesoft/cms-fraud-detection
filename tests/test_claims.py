"""Tests for GET /api/claims — paginated provider-service cases."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.claims import router

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

SAMPLE_CASE = {
    "case_id": "1234567890-99213",
    "npi": "1234567890",
    "provider_last_org_name": "ACME MEDICAL",
    "provider_first_name": "JANE",
    "provider_credentials": "M.D.",
    "provider_entity_code": "I",
    "provider_city": "Los Angeles",
    "provider_state": "CA",
    "provider_zip5": "90001",
    "provider_type": "Internal Medicine",
    "medicare_participating_ind": "Y",
    "hcpcs_cd": "99213",
    "hcpcs_desc": "Office/outpatient visit est",
    "place_of_service": "F",
    "tot_benes": 50.0,
    "tot_srvcs": 200.0,
    "tot_bene_day_srvcs": 150.0,
    "avg_submitted_charge": 120.0,
    "avg_medicare_allowed_amt": 80.0,
    "avg_medicare_payment_amt": 65.0,
    "estimated_case_payment_amt": 13000.0,
    "services_per_bene": 4.0,
    "submitted_to_allowed_ratio": 1.5,
    "payment_to_allowed_ratio": 0.81,
    "peer_scope": "state_specific",
    "peer_case_count": 45,
    "peer_avg_tot_srvcs": 120.0,
    "service_volume_peer_z": 2.5,
    "services_per_bene_peer_z": 1.2,
    "submitted_to_allowed_peer_z": 0.8,
    "payment_peer_z": 0.5,
    "seed_risk_score": 42,
    "seed_legitimacy_score": 55,
    "seed_case_label": "review",
    "seed_risk_reasons": "volume outlier",
    "seed_legitimacy_reasons": "enrolled, no revocation",
}


class _ListCursor:
    def __init__(self, count: int, rows: list[dict]):
        self._count = count
        self._rows = rows
        self._call = 0

    async def execute(self, sql: str, params: list | None = None):
        self._call += 1

    async def fetchone(self) -> dict | None:
        return {"cnt": self._count}

    async def fetchall(self) -> list[dict]:
        return self._rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _SingleCursor:
    """Cursor for single-row lookup (get_claim endpoint)."""

    def __init__(self, row: dict | None):
        self._row = row

    async def execute(self, sql: str, params: tuple | None = None):
        pass

    async def fetchone(self) -> dict | None:
        return self._row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _SingleConn:
    def __init__(self, row: dict | None):
        self._row = row

    def cursor(self, row_factory=None):
        return _SingleCursor(self._row)


class _FakeConn:
    def __init__(self, rows: list[dict], count: int | None = None):
        self._rows = rows
        self._count = count if count is not None else len(rows)

    def cursor(self, row_factory=None):
        return _ListCursor(self._count, self._rows)


def _make_app(rows: list[dict], count: int | None = None) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(rows, count)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


def _make_single_app(row: dict | None) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _SingleConn(row)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Tests — list endpoint
# ---------------------------------------------------------------------------


class TestListClaims:
    async def test_returns_data(self):
        app = _make_app([SAMPLE_CASE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["case_id"] == "1234567890-99213"
        assert body["data"][0]["npi"] == "1234567890"
        assert body["data"][0]["seed_case_label"] == "review"
        assert body["meta"]["total"] == 1

    async def test_empty_list(self):
        app = _make_app([], count=0)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims")

        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0
        assert body["meta"]["pages"] == 0

    async def test_pagination_meta(self):
        app = _make_app([SAMPLE_CASE], count=250)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims?page=3&per_page=100")

        body = resp.json()
        assert body["meta"]["page"] == 3
        assert body["meta"]["per_page"] == 100
        assert body["meta"]["total"] == 250
        assert body["meta"]["pages"] == 3


# ---------------------------------------------------------------------------
# Tests — filters
# ---------------------------------------------------------------------------


class TestClaimFilters:
    async def test_filter_by_npi(self):
        app = _make_app([SAMPLE_CASE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims?npi=1234567890")

        assert resp.status_code == 200

    async def test_filter_by_case_label(self):
        app = _make_app([SAMPLE_CASE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims?case_label=review")

        assert resp.status_code == 200

    async def test_filter_by_state(self):
        app = _make_app([SAMPLE_CASE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims?state=CA")

        assert resp.status_code == 200

    async def test_filter_by_risk_range(self):
        app = _make_app([SAMPLE_CASE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims?risk_min=30&risk_max=60")

        assert resp.status_code == 200

    async def test_combined_filters(self):
        app = _make_app([SAMPLE_CASE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/claims?state=CA&provider_type=Internal+Medicine&case_label=review&risk_min=30"
            )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — validation
# ---------------------------------------------------------------------------


class TestClaimValidation:
    async def test_per_page_too_high(self):
        app = _make_app([])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims?per_page=999")

        assert resp.status_code == 422

    async def test_risk_min_out_of_range(self):
        app = _make_app([])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims?risk_min=-1")

        assert resp.status_code == 422

    async def test_response_structure(self):
        app = _make_app([SAMPLE_CASE])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims")

        body = resp.json()
        claim = body["data"][0]
        assert "case_id" in claim
        assert "npi" in claim
        assert "hcpcs_cd" in claim
        assert "seed_risk_score" in claim
        assert "seed_case_label" in claim
        assert "peer_case_count" in claim


# ---------------------------------------------------------------------------
# Tests — get single claim
# ---------------------------------------------------------------------------


class TestGetClaim:
    async def test_returns_claim(self):
        app = _make_single_app(SAMPLE_CASE)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims/1234567890-99213")

        assert resp.status_code == 200
        body = resp.json()
        assert body["case_id"] == "1234567890-99213"
        assert body["npi"] == "1234567890"
        assert body["seed_case_label"] == "review"

    async def test_not_found(self):
        app = _make_single_app(None)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims/nonexistent-case")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Claim not found"

    async def test_response_structure(self):
        app = _make_single_app(SAMPLE_CASE)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/claims/1234567890-99213")

        body = resp.json()
        assert "case_id" in body
        assert "npi" in body
        assert "hcpcs_cd" in body
        assert "seed_risk_score" in body
        assert "seed_case_label" in body
