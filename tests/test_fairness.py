"""Tests for GET /api/fairness — flagging rate analysis by geography and specialty."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.fairness import _build_cohorts, _compute_parity, _std_of_rates, router
from src.api.schemas import CohortFairness

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

# 3 queries: overall, by_state, by_specialty
OVERALL_ROW = {"total": 100, "flagged": 20}

STATE_ROWS = [
    {"cohort": "CA", "provider_count": 40, "flagged_count": 12},
    {"cohort": "NY", "provider_count": 30, "flagged_count": 5},
    {"cohort": "TX", "provider_count": 30, "flagged_count": 3},
]

SPECIALTY_ROWS = [
    {"cohort": "Internal Medicine", "provider_count": 50, "flagged_count": 10},
    {"cohort": "Cardiology", "provider_count": 30, "flagged_count": 8},
    {"cohort": "Family Practice", "provider_count": 20, "flagged_count": 2},
]


class _FairnessCursor:
    """Returns canned results matching endpoint query order (non-blind mode):

    1. overall → fetchone  2. by_state → fetchall  3. by_specialty → fetchall

    WARNING: If the endpoint reorders its SQL calls, these tests will silently
    return wrong data. Keep query order in sync with fairness.py:get_fairness.
    """

    def __init__(self, overall: dict, states: list[dict], specialties: list[dict]):
        self._results: list = [overall, states, specialties]
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


class _FakeConn:
    def __init__(
        self,
        overall: dict = OVERALL_ROW,
        states: list[dict] = STATE_ROWS,
        specialties: list[dict] = SPECIALTY_ROWS,
    ):
        self._overall = overall
        self._states = states
        self._specialties = specialties

    def cursor(self, row_factory=None):
        return _FairnessCursor(self._overall, self._states, self._specialties)


def _make_app(
    overall: dict = OVERALL_ROW,
    states: list[dict] = STATE_ROWS,
    specialties: list[dict] = SPECIALTY_ROWS,
) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(overall, states, specialties)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Tests — endpoint integration
# ---------------------------------------------------------------------------


class TestFairnessEndpoint:
    async def test_returns_200(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness")

        assert resp.status_code == 200

    async def test_response_structure(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness")

        body = resp.json()
        assert "by_state" in body
        assert "by_specialty" in body
        assert "overall_flagging_rate" in body
        assert "statistical_parity_diff" in body
        assert "disparate_impact_ratio" in body

    async def test_overall_flagging_rate(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness")

        body = resp.json()
        assert body["overall_flagging_rate"] == 0.2  # 20/100

    async def test_state_cohorts_present(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness")

        body = resp.json()
        cohort_names = [c["cohort"] for c in body["by_state"]]
        assert "CA" in cohort_names
        assert "NY" in cohort_names
        assert "TX" in cohort_names

    async def test_specialty_cohorts_present(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness")

        body = resp.json()
        cohort_names = [c["cohort"] for c in body["by_specialty"]]
        assert "Internal Medicine" in cohort_names
        assert "Cardiology" in cohort_names

    async def test_custom_threshold(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness?threshold=30")

        assert resp.status_code == 200

    async def test_empty_data(self):
        app = _make_app(
            overall={"total": 0, "flagged": 0},
            states=[],
            specialties=[],
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness")

        body = resp.json()
        assert body["overall_flagging_rate"] == 0.0
        assert body["by_state"] == []
        assert body["by_specialty"] == []


# ---------------------------------------------------------------------------
# Tests — pure function unit tests
# ---------------------------------------------------------------------------


class TestBuildCohorts:
    def test_flagging_rates(self):
        cohorts = _build_cohorts(STATE_ROWS, 0.2, 0.05)
        rates = {c.cohort: c.flagging_rate for c in cohorts}
        assert rates["CA"] == 0.3  # 12/40
        assert rates["TX"] == 0.1  # 3/30

    def test_outlier_detection(self):
        # CA rate=0.3, overall=0.2, std=0.05 → (0.3-0.2)=0.1 > 2*0.05=0.1 → False (not strictly >)
        # Make a clear outlier
        rows = [
            {"cohort": "OUTLIER", "provider_count": 10, "flagged_count": 9},
            {"cohort": "NORMAL", "provider_count": 90, "flagged_count": 5},
        ]
        cohorts = _build_cohorts(rows, 0.14, 0.05)
        outlier = next(c for c in cohorts if c.cohort == "OUTLIER")
        normal = next(c for c in cohorts if c.cohort == "NORMAL")
        assert outlier.is_outlier is True
        assert normal.is_outlier is False

    def test_zero_count_cohort(self):
        rows = [{"cohort": "EMPTY", "provider_count": 0, "flagged_count": 0}]
        cohorts = _build_cohorts(rows, 0.2, 0.05)
        assert cohorts[0].flagging_rate == 0.0
        assert cohorts[0].is_outlier is False


class TestComputeParity:
    def test_parity_metrics(self):
        cohorts = [
            CohortFairness(
                cohort="A", provider_count=50, flagged_count=10, flagging_rate=0.2, is_outlier=False
            ),
            CohortFairness(
                cohort="B", provider_count=50, flagged_count=5, flagging_rate=0.1, is_outlier=False
            ),
        ]
        spd, di = _compute_parity(cohorts)
        assert spd == 0.1  # 0.2 - 0.1
        assert di == 0.5  # 0.1 / 0.2

    def test_single_cohort_returns_none(self):
        cohorts = [
            CohortFairness(
                cohort="A", provider_count=50, flagged_count=10, flagging_rate=0.2, is_outlier=False
            ),
        ]
        spd, di = _compute_parity(cohorts)
        assert spd is None
        assert di is None

    def test_perfect_parity(self):
        cohorts = [
            CohortFairness(
                cohort="A", provider_count=50, flagged_count=10, flagging_rate=0.2, is_outlier=False
            ),
            CohortFairness(
                cohort="B", provider_count=50, flagged_count=10, flagging_rate=0.2, is_outlier=False
            ),
        ]
        spd, di = _compute_parity(cohorts)
        assert spd == 0.0
        assert di == 1.0


class TestStdOfRates:
    def test_basic_std(self):
        rows = [
            {"provider_count": 100, "flagged_count": 20},
            {"provider_count": 100, "flagged_count": 40},
        ]
        std = _std_of_rates(rows)
        assert std == 0.1  # rates: 0.2, 0.4 → mean=0.3, std=0.1

    def test_single_row(self):
        rows = [{"provider_count": 100, "flagged_count": 20}]
        assert _std_of_rates(rows) == 0.0

    def test_empty(self):
        assert _std_of_rates([]) == 0.0


# ---------------------------------------------------------------------------
# Tests — blind mode (revocation-blind fairness analysis)
# ---------------------------------------------------------------------------

# When blind=true, the endpoint runs 6 queries:
# 1. blind overall, 2. blind state, 3. blind specialty,
# 4. orig overall, 5. orig state (for comparison)
BLIND_OVERALL_ROW = {"total": 100, "flagged": 15}  # fewer flagged without revocation
BLIND_STATE_ROWS = [
    {"cohort": "CA", "provider_count": 40, "flagged_count": 9},
    {"cohort": "NY", "provider_count": 30, "flagged_count": 4},
    {"cohort": "TX", "provider_count": 30, "flagged_count": 2},
]
BLIND_SPECIALTY_ROWS = [
    {"cohort": "Internal Medicine", "provider_count": 50, "flagged_count": 8},
    {"cohort": "Cardiology", "provider_count": 30, "flagged_count": 5},
    {"cohort": "Family Practice", "provider_count": 20, "flagged_count": 2},
]


class _BlindFairnessCursor:
    """Handles 5 queries for blind mode matching fairness.py:get_fairness query order:

    1. blind overall (fetchone)  2. blind state (fetchall)
    3. blind specialty (fetchall)  4. orig overall (fetchone)
    5. orig state (fetchall) — for orig disparate_impact

    WARNING: Keep in sync with fairness.py:get_fairness blind=true code path.
    """

    def __init__(self):
        self._results: list = [
            BLIND_OVERALL_ROW,
            BLIND_STATE_ROWS,
            BLIND_SPECIALTY_ROWS,
            OVERALL_ROW,
            STATE_ROWS,
        ]
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


class _BlindFakeConn:
    def cursor(self, row_factory=None):
        return _BlindFairnessCursor()


def _make_blind_app() -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _BlindFakeConn()

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


class TestFairnessBlindMode:
    @pytest.mark.anyio
    async def test_blind_returns_200(self):
        app = _make_blind_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness?blind=true")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_blind_includes_revocation_impact(self):
        app = _make_blind_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness?blind=true")
        body = resp.json()
        assert body["revocation_impact"] is not None
        impact = body["revocation_impact"]
        assert "overall_flagging_rate_with" in impact
        assert "overall_flagging_rate_without" in impact
        assert "flagging_rate_delta" in impact

    @pytest.mark.anyio
    async def test_blind_flagging_rate_lower(self):
        """Removing revocation signal should reduce flagging rate."""
        app = _make_blind_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness?blind=true")
        body = resp.json()
        # Blind overall = 15/100 = 0.15, original = 20/100 = 0.20
        assert body["overall_flagging_rate"] == 0.15
        impact = body["revocation_impact"]
        assert impact["overall_flagging_rate_with"] == 0.2
        assert impact["overall_flagging_rate_without"] == 0.15
        assert impact["flagging_rate_delta"] == -0.05  # 0.15 - 0.20

    @pytest.mark.anyio
    async def test_blind_has_disparate_impact_comparison(self):
        app = _make_blind_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness?blind=true")
        body = resp.json()
        impact = body["revocation_impact"]
        assert impact["disparate_impact_with"] is not None
        assert impact["disparate_impact_without"] is not None

    @pytest.mark.anyio
    async def test_non_blind_no_revocation_impact(self):
        """Normal mode should NOT include revocation_impact."""
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/fairness?blind=false")
        body = resp.json()
        assert body["revocation_impact"] is None
