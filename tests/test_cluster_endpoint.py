"""Tests for GET /api/cluster/{npi} — route-level with mocked DB."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI

from src.api.deps import get_db
from src.api.routes.cluster import router
from src.api.schemas import ClusterMember, FraudClusterResponse

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

SEED_EXISTS = {"?column?": 1}

CLUSTER_ROWS = [
    {
        "npi": "9999999999",
        "provider_name": "Bad Clinic",
        "provider_type": "Cardiology",
        "state": "FL",
        "zip5": "33101",
        "risk_score": 78,
        "revoked": 1,
        "link_type": "SAME_ZIP",
        "hops": 1,
    },
    {
        "npi": "8888888888",
        "provider_name": "Shady Lab",
        "provider_type": "Clinical Laboratory",
        "state": "FL",
        "zip5": "33101",
        "risk_score": 55,
        "revoked": 0,
        "link_type": "SAME_ZIP",
        "hops": 2,
    },
]


class _ClusterCursor:
    """Returns canned results based on query call order:
    1. seed exists check (fetchone)
    2. cluster members (fetchall)
    """

    def __init__(self, seed: dict | None, members: list[dict]):
        self._results: list = [seed, members]
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
        seed: dict | None = SEED_EXISTS,
        members: list[dict] | None = None,
    ):
        self._seed = seed
        self._members = members if members is not None else CLUSTER_ROWS

    def cursor(self, row_factory=None):
        return _ClusterCursor(self._seed, self._members)


def _make_app(
    seed: dict | None = SEED_EXISTS,
    members: list[dict] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    conn = _FakeConn(seed, members)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db
    return test_app


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------


class TestClusterSchemas:
    def test_cluster_member_defaults(self):
        m = ClusterMember(npi="1234567890", link_type="SAME_ZIP", hops=1)
        assert m.provider_name is None
        assert m.risk_score is None
        assert m.revoked is False
        assert m.risk_band is None

    def test_fraud_cluster_response_defaults(self):
        r = FraudClusterResponse(npi="1234567890", cluster_id="1234567890")
        assert r.members == []
        assert r.cluster_size == 0
        assert r.high_risk_count == 0
        assert r.revoked_count == 0
        assert r.truncated is False


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestClusterEndpoint:
    @pytest.mark.anyio
    async def test_returns_200(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_response_structure(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        assert body["npi"] == "1234567890"
        assert "cluster_id" in body
        assert "members" in body
        assert "cluster_size" in body
        assert "high_risk_count" in body
        assert "revoked_count" in body
        assert "truncated" in body

    @pytest.mark.anyio
    async def test_members_populated(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        assert len(body["members"]) == 2
        m0 = body["members"][0]
        assert m0["npi"] == "9999999999"
        assert m0["risk_score"] == 78
        assert m0["link_type"] == "SAME_ZIP"
        assert m0["hops"] == 1
        assert m0["revoked"] is True
        assert m0["risk_band"] == "high_risk"

    @pytest.mark.anyio
    async def test_cluster_size_includes_seed(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        # 2 members + seed = 3
        assert body["cluster_size"] == 3

    @pytest.mark.anyio
    async def test_high_risk_and_revoked_counts(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        assert body["high_risk_count"] == 2  # 9999999999 (78) + 8888888888 (55)
        assert body["revoked_count"] == 1

    @pytest.mark.anyio
    async def test_cluster_id_deterministic(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        expected = "_".join(sorted(["1234567890", "9999999999", "8888888888"]))
        assert body["cluster_id"] == expected

    @pytest.mark.anyio
    async def test_unknown_provider_returns_404(self):
        app = _make_app(seed=None)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/0000000000")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_isolated_provider_returns_empty_members(self):
        app = _make_app(members=[])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        assert resp.status_code == 200
        assert body["members"] == []
        assert body["cluster_size"] == 1  # seed only
        assert body["high_risk_count"] == 0

    @pytest.mark.anyio
    async def test_truncation_flag(self):
        # 26 rows triggers truncation (> 25)
        many_rows = [
            {
                "npi": f"100000000{i:01d}" if i < 10 else f"10000000{i:02d}",
                "provider_name": f"Clinic {i}",
                "provider_type": "Internal Medicine",
                "state": "FL",
                "zip5": "33101",
                "risk_score": 55,
                "revoked": 0,
                "link_type": "SAME_ZIP",
                "hops": 1,
            }
            for i in range(26)
        ]
        app = _make_app(members=many_rows)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        assert body["truncated"] is True
        assert len(body["members"]) == 25

    @pytest.mark.anyio
    async def test_risk_band_assignment(self):
        rows = [
            {**CLUSTER_ROWS[0], "risk_score": 55},  # high_risk
            {**CLUSTER_ROWS[1], "npi": "7777777777", "risk_score": 30},  # review
            {
                "npi": "6666666666",
                "provider_name": "Good Clinic",
                "provider_type": "Family Medicine",
                "state": "FL",
                "zip5": "33101",
                "risk_score": 5,
                "revoked": 0,
                "link_type": "SAME_ZIP",
                "hops": 1,
            },  # stable
        ]
        app = _make_app(members=rows)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/cluster/1234567890")
        body = resp.json()
        bands = {m["npi"]: m["risk_band"] for m in body["members"]}
        assert bands["9999999999"] == "high_risk"
        assert bands["7777777777"] == "review"
        assert bands["6666666666"] == "stable"
