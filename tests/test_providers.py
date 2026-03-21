"""Tests for /api/providers endpoints."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.providers import router

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ROW = {
    "npi": "1234567890",
    "provider_name": "ACME MEDICAL",
    "provider_type": "Internal Medicine",
    "state": "CA",
    "city": "Los Angeles",
    "entity_code": "I",
    "max_seed_risk_score": 72,
    "service_line_count": 15,
    "total_estimated_payment": 50000.0,
    "revoked_2026": 0,
    # Extra columns returned by SELECT * (detail endpoint)
    "zip5": "90001",
    "medicare_participating": "Y",
    "enrolled_2025": 1,
    "enrollment_record_count": 2,
    "revocation_reason": None,
    "provider_total_hcpcs_codes": 10.0,
    "provider_total_benes": 100.0,
    "provider_total_services": 500.0,
    "provider_total_payment_amt": 50000.0,
    "unique_hcpcs_codes": 8,
    "unique_place_of_service": 2,
    "total_benes": 100.0,
    "total_services": 500.0,
    "total_bene_day_services": 300.0,
    "avg_benes_per_line": 6.7,
    "avg_services_per_line": 33.3,
    "avg_services_per_bene": 5.0,
    "max_services_per_bene": 12.0,
    "std_services_per_bene": 2.5,
    "mean_submitted_charge": 200.0,
    "max_submitted_charge": 800.0,
    "std_submitted_charge": 150.0,
    "mean_allowed_amt": 150.0,
    "max_allowed_amt": 600.0,
    "mean_payment_amt": 120.0,
    "max_payment_amt": 500.0,
    "std_payment_amt": 80.0,
    "mean_charge_ratio": 1.33,
    "max_charge_ratio": 2.0,
    "std_charge_ratio": 0.5,
    "mean_payment_ratio": 0.8,
    "service_hhi": 0.25,
    "top_code_share": 0.4,
    "top3_code_share": 0.7,
    "mean_volume_z": 1.5,
    "max_volume_z": 2.8,
    "mean_intensity_z": 0.9,
    "max_intensity_z": 1.7,
    "mean_charge_z": 1.2,
    "max_charge_z": 2.1,
    "mean_payment_z": 0.7,
    "max_payment_z": 1.4,
    "n_volume_outlier_lines": 3,
    "n_intensity_outlier_lines": 1,
    "n_charge_outlier_lines": 2,
    "avg_seed_risk_score": 65.0,
    "min_seed_legitimacy_score": 30,
    "avg_seed_legitimacy_score": 45.0,
    "n_high_risk_lines": 5,
    "n_state_peer_lines": 10,
    "risk_legitimacy_gap": 42,
    "frac_volume_outlier_lines": 0.2,
    "charge_cv": 0.75,
}

SUMMARY_KEYS = {
    "npi",
    "provider_name",
    "provider_type",
    "state",
    "city",
    "entity_code",
    "max_seed_risk_score",
    "service_line_count",
    "total_estimated_payment",
    "revoked_2026",
}


def _summary_row(overrides: dict | None = None) -> dict:
    """Return only the summary columns from SAMPLE_ROW."""
    row = {k: SAMPLE_ROW[k] for k in SUMMARY_KEYS}
    if overrides:
        row.update(overrides)
    return row


class FakeCursor:
    """Minimal async cursor mock that returns configurable rows."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._called_sql: list[str] = []

    async def execute(self, sql: str, params: list | None = None):
        self._called_sql.append(sql)

    async def fetchone(self) -> dict | None:
        return self._rows[0] if self._rows else None

    async def fetchall(self) -> list[dict]:
        return self._rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _ListCursor:
    """Cursor for list endpoint: first execute is COUNT, second is SELECT rows."""

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


class _DetailCursor:
    """Cursor for detail endpoint: single execute, fetchone returns the row."""

    def __init__(self, row: dict | None):
        self._row = row

    async def execute(self, sql: str, params: list | None = None):
        pass

    async def fetchone(self) -> dict | None:
        return self._row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeListConn:
    def __init__(self, rows: list[dict], count: int | None = None):
        self._rows = rows
        self._count = count if count is not None else len(rows)

    def cursor(self, row_factory=None):
        return _ListCursor(self._count, self._rows)


class FakeDetailConn:
    def __init__(self, row: dict | None):
        self._row = row

    def cursor(self, row_factory=None):
        return _DetailCursor(self._row)


def _make_app(rows: list[dict], count: int | None = None, detail: bool = False) -> FastAPI:
    """Build a test app with a fake DB dependency."""

    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    if detail:
        conn = FakeDetailConn(rows[0] if rows else None)
    else:
        conn = FakeListConn(rows, count)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Tests — list endpoint
# ---------------------------------------------------------------------------


class TestListProviders:
    async def test_list_returns_data(self):
        app = _make_app([_summary_row()])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["npi"] == "1234567890"
        assert body["data"][0]["risk_band"] == "high_risk"
        assert body["meta"]["total"] == 1

    async def test_empty_list(self):
        app = _make_app([], count=0)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0
        assert body["meta"]["pages"] == 0

    async def test_pagination_meta(self):
        app = _make_app([_summary_row()], count=120)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers?page=2&per_page=50")

        body = resp.json()
        assert body["meta"]["page"] == 2
        assert body["meta"]["per_page"] == 50
        assert body["meta"]["total"] == 120
        assert body["meta"]["pages"] == 3  # ceil(120/50)

    async def test_filter_params_accepted(self):
        app = _make_app([_summary_row()])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/providers?state=CA&provider_type=Internal+Medicine&risk_band=high_risk&q=ACME"
            )

        assert resp.status_code == 200

    async def test_risk_band_computed(self):
        """risk_band is not in DB — it should be computed from max_seed_risk_score."""
        row = _summary_row({"max_seed_risk_score": 35})
        app = _make_app([row])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers")

        assert resp.json()["data"][0]["risk_band"] == "review"

    async def test_per_page_validation(self):
        app = _make_app([])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers?per_page=999")

        assert resp.status_code == 422  # exceeds le=200


# ---------------------------------------------------------------------------
# Tests — detail endpoint
# ---------------------------------------------------------------------------


class TestGetProvider:
    async def test_detail_returns_full_profile(self):
        app = _make_app([SAMPLE_ROW], detail=True)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890")

        assert resp.status_code == 200
        body = resp.json()
        assert body["npi"] == "1234567890"
        assert body["risk_band"] == "high_risk"
        assert body["mean_volume_z"] == 1.5
        assert body["n_high_risk_lines"] == 5

    async def test_detail_not_found(self):
        app = _make_app([], detail=True)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/0000000000")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    async def test_detail_risk_band_stable(self):
        row = {**SAMPLE_ROW, "max_seed_risk_score": 15}
        app = _make_app([row], detail=True)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890")

        assert resp.json()["risk_band"] == "stable"


# ---------------------------------------------------------------------------
# Tests — radar endpoint
# ---------------------------------------------------------------------------


class TestGetProviderRadar:
    async def test_radar_returns_dimensions(self):
        app = _make_app([SAMPLE_ROW], detail=True)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/radar")

        assert resp.status_code == 200
        body = resp.json()
        assert body["npi"] == "1234567890"
        assert len(body["dimensions"]) == 8
        names = [d["dimension"] for d in body["dimensions"]]
        assert "Volume" in names
        assert "Concentration" in names
        assert "Enrollment" in names

    async def test_radar_z_score_mapping(self):
        """mean_volume_z=1.5 should map to 50 + 1.5*10 = 65."""
        app = _make_app([SAMPLE_ROW], detail=True)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/radar")

        dims = {d["dimension"]: d for d in resp.json()["dimensions"]}
        assert dims["Volume"]["provider"] == 65.0  # 50 + 1.5 * 10
        assert dims["Volume"]["peer"] == 50.0

    async def test_radar_enrollment_inverted(self):
        """enrolled_2025=1 means low risk → provider=0.0 on Enrollment axis."""
        app = _make_app([SAMPLE_ROW], detail=True)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/1234567890/radar")

        dims = {d["dimension"]: d for d in resp.json()["dimensions"]}
        assert dims["Enrollment"]["provider"] == 0.0  # enrolled = no risk

    async def test_radar_not_found(self):
        app = _make_app([], detail=True)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers/0000000000/radar")

        assert resp.status_code == 404
