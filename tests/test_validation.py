"""Tests for GET /api/validation — retrospective detection rate statistics."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.routes.validation import _load_report, router
from src.api.schemas import ValidationReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_DATA = {
    "summary": {
        "total_revoked_cases": 862,
        "total_revoked_npis": 335,
        "case_detection_rate": 0.9037,
        "npi_detection_rate": 0.9134,
        "avg_blind_risk_score_revoked": 20.4,
        "avg_risk_score_non_revoked": 41.4,
        "risk_score_lift": -21.0,
    },
    "non_revoked_baseline": {
        "high_risk": 17,
        "review": 6346,
        "stable": 6000,
    },
    "by_revocation_reason": {
        "424.535(A)(9) Failure To Report;424.535(A)(3) Felonies": {
            "total": 106,
            "high_risk": 0,
            "review": 106,
            "stable": 0,
            "detection_rate": 1.0,
        },
        "424.535(A)(8)(Ii) Abuse Of Billing Privileges: Pattern Or Practice": {
            "total": 34,
            "high_risk": 0,
            "review": 32,
            "stable": 2,
            "detection_rate": 0.9411764705882353,
        },
    },
}


def _make_app() -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")
    return test_app


# ---------------------------------------------------------------------------
# Endpoint integration tests
# ---------------------------------------------------------------------------


class TestValidationEndpoint:
    @pytest.mark.anyio
    async def test_returns_200(self):
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/validation")

        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_response_structure(self):
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/validation")

        assert resp.status_code == 200
        body = resp.json()
        assert "overall_detection_rate" in body
        assert "total_revoked_providers" in body
        assert "total_revoked_cases" in body
        assert "detection_by_reason" in body
        assert "baseline_flagging_rate" in body
        assert "methodology" in body

    @pytest.mark.anyio
    async def test_known_values(self):
        """Values must match retrospective_results.json exactly."""
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/validation")

        body = resp.json()
        assert body["overall_detection_rate"] == 0.9134
        assert body["total_revoked_providers"] == 335
        assert body["total_revoked_cases"] == 862

    @pytest.mark.anyio
    async def test_baseline_flagging_rate(self):
        """Baseline = (high_risk + review) / total non-revoked = (17+6346)/12363 ≈ 0.5147."""
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/validation")

        body = resp.json()
        # 17 + 6346 = 6363; total = 17 + 6346 + 6000 = 12363
        expected = round(6363 / 12363, 4)
        assert body["baseline_flagging_rate"] == expected

    @pytest.mark.anyio
    async def test_detection_by_reason_sorted_descending(self):
        """Reasons should be sorted by count descending."""
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/validation")

        body = resp.json()
        counts = [r["count"] for r in body["detection_by_reason"]]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.anyio
    async def test_detection_by_reason_fields(self):
        """Each reason entry must have required fields."""
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/validation")

        body = resp.json()
        assert len(body["detection_by_reason"]) > 0
        for entry in body["detection_by_reason"]:
            assert "reason" in entry
            assert "count" in entry
            assert "detected" in entry
            assert "rate" in entry
            assert 0.0 <= entry["rate"] <= 1.0

    @pytest.mark.anyio
    async def test_methodology_is_non_empty_string(self):
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/validation")

        body = resp.json()
        assert isinstance(body["methodology"], str)
        assert len(body["methodology"]) > 50

    @pytest.mark.anyio
    async def test_idempotent_multiple_calls(self):
        """Second call returns same data (lru_cache is stable)."""
        app = _make_app()
        _load_report.cache_clear()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/validation")
            resp2 = await client.get("/api/validation")

        assert resp1.json() == resp2.json()


# ---------------------------------------------------------------------------
# Unit test: _load_report parses sample data correctly
# ---------------------------------------------------------------------------


class TestLoadReport:
    def test_parses_sample_data(self, tmp_path):
        import json

        data_file = tmp_path / "retrospective_results.json"
        data_file.write_text(json.dumps(_SAMPLE_DATA))

        _load_report.cache_clear()
        with patch("src.api.routes.validation._DATA_FILE", data_file):
            report = _load_report()

        assert isinstance(report, ValidationReport)
        assert report.overall_detection_rate == 0.9134
        assert report.total_revoked_providers == 335
        assert report.total_revoked_cases == 862
        assert len(report.detection_by_reason) == 2
        # Sorted descending: felonies (106) before billing abuse (34)
        assert report.detection_by_reason[0].count == 106
        assert report.detection_by_reason[1].count == 34

    def test_detected_count_excludes_stable(self, tmp_path):
        import json

        data_file = tmp_path / "retrospective_results.json"
        data_file.write_text(json.dumps(_SAMPLE_DATA))

        _load_report.cache_clear()
        with patch("src.api.routes.validation._DATA_FILE", data_file):
            report = _load_report()

        # billing abuse: total=34, stable=2 → detected=32
        billing = next(
            r
            for r in report.detection_by_reason
            if "Billing" in r.reason or "billing" in r.reason.lower()
        )
        assert billing.detected == 32

    def test_baseline_rate_calculation(self, tmp_path):
        import json

        data_file = tmp_path / "retrospective_results.json"
        data_file.write_text(json.dumps(_SAMPLE_DATA))

        _load_report.cache_clear()
        with patch("src.api.routes.validation._DATA_FILE", data_file):
            report = _load_report()

        # (17 + 6346) / (17 + 6346 + 6000) = 6363 / 12363
        expected = round(6363 / 12363, 4)
        assert report.baseline_flagging_rate == expected
