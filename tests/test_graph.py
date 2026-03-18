"""Tests for GET /api/graph/{npi} — evidence graph endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.graph_client import get_graph_db
from src.api.routes.graph import _build_graph, _node_id, _node_label, router

# ---------------------------------------------------------------------------
# Fake Neo4j node / relationship objects
# ---------------------------------------------------------------------------


class FakeNode:
    """Mimics the neo4j.graph.Node interface used by _build_graph."""

    def __init__(self, label: str, props: dict, element_id: str = "0"):
        self.labels = frozenset([label])
        self._props = props
        self.element_id = element_id

    def __iter__(self):
        return iter(self._props)

    def __getitem__(self, key: str):
        return self._props[key]

    def keys(self):
        return self._props.keys()

    def values(self):
        return self._props.values()

    def items(self):
        return self._props.items()


class FakeRel:
    """Mimics the neo4j.graph.Relationship interface."""

    def __init__(self, rel_type: str, props: dict | None = None):
        self.type = rel_type
        self._props = props or {}

    def __iter__(self):
        return iter(self._props)

    def __getitem__(self, key: str):
        return self._props[key]

    def keys(self):
        return self._props.keys()

    def values(self):
        return self._props.values()

    def items(self):
        return self._props.items()


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

PROVIDER_NODE = FakeNode("Provider", {"npi": "1234567890", "name": "TEST CLINIC", "state": "CA"})
CASE_NODE = FakeNode(
    "Case", {"case_id": "1234567890_99213", "hcpcs_cd": "99213", "label": "review"}
)
SIGNAL_NODE = FakeNode("Signal", {"name": "service_volume_outlier", "category": "peer"})
PEER_NODE = FakeNode(
    "PeerGroup",
    {
        "key": "Internal Medicine|99213|state",
        "specialty": "Internal Medicine",
        "hcpcs_cd": "99213",
    },
)
SOURCE_NODE = FakeNode(
    "Source",
    {"dataset": "Medicare Physician & Other Practitioners", "year": "2022"},
)

HAS_CASE_REL = FakeRel("HAS_CASE")
HAS_SIGNAL_REL = FakeRel("HAS_SIGNAL", {"value": 3.5, "points": 14})
IN_PEER_REL = FakeRel("IN_PEER_GROUP")
SOURCED_FROM_REL = FakeRel("SOURCED_FROM")

FULL_RECORD = {
    "p": PROVIDER_NODE,
    "hc": HAS_CASE_REL,
    "c": CASE_NODE,
    "hs": HAS_SIGNAL_REL,
    "s": SIGNAL_NODE,
    "ip": IN_PEER_REL,
    "pg": PEER_NODE,
    "sf": SOURCED_FROM_REL,
    "src": SOURCE_NODE,
}


# ---------------------------------------------------------------------------
# Unit tests — helper functions
# ---------------------------------------------------------------------------


class TestNodeId:
    def test_provider_id(self):
        assert _node_id(PROVIDER_NODE) == "provider:1234567890"

    def test_case_id(self):
        assert _node_id(CASE_NODE) == "case:1234567890_99213"

    def test_signal_id(self):
        assert _node_id(SIGNAL_NODE) == "signal:service_volume_outlier"

    def test_peergroup_id(self):
        assert _node_id(PEER_NODE) == "peergroup:Internal Medicine|99213|state"

    def test_source_id(self):
        assert _node_id(SOURCE_NODE) == "source:Medicare Physician & Other Practitioners"


class TestNodeLabel:
    def test_provider_label(self):
        assert _node_label(PROVIDER_NODE) == "TEST CLINIC"

    def test_case_label(self):
        assert _node_label(CASE_NODE) == "99213"

    def test_signal_label(self):
        assert _node_label(SIGNAL_NODE) == "service_volume_outlier"

    def test_peergroup_label(self):
        assert _node_label(PEER_NODE) == "Internal Medicine / 99213"

    def test_source_label(self):
        assert _node_label(SOURCE_NODE) == "Medicare Physician & Other Practitioners"


class TestBuildGraph:
    def test_full_record(self):
        nodes, edges = _build_graph([FULL_RECORD])
        assert len(nodes) == 5
        assert len(edges) == 4
        node_types = {n.type for n in nodes}
        assert node_types == {"Provider", "Case", "Signal", "PeerGroup", "Source"}

    def test_deduplicates_nodes(self):
        """Same record twice should not duplicate nodes or edges."""
        nodes, edges = _build_graph([FULL_RECORD, FULL_RECORD])
        assert len(nodes) == 5
        assert len(edges) == 4

    def test_null_optional_nodes(self):
        """Record with only provider (no cases) — no edges."""
        record = {
            "p": PROVIDER_NODE,
            "hc": None,
            "c": None,
            "hs": None,
            "s": None,
            "ip": None,
            "pg": None,
            "sf": None,
            "src": None,
        }
        nodes, edges = _build_graph([record])
        assert len(nodes) == 1
        assert len(edges) == 0
        assert nodes[0].type == "Provider"

    def test_edge_properties_preserved(self):
        nodes, edges = _build_graph([FULL_RECORD])
        has_signal = [e for e in edges if e.type == "HAS_SIGNAL"]
        assert len(has_signal) == 1
        assert has_signal[0].properties["value"] == 3.5
        assert has_signal[0].properties["points"] == 14


# ---------------------------------------------------------------------------
# Integration tests — HTTP endpoint
# ---------------------------------------------------------------------------


class _FakeResult:
    def __init__(self, records: list[dict]):
        self._records = records

    async def fetch(self, n: int) -> list:
        return [_DictRecord(r) for r in self._records]


class _DictRecord:
    """Wraps a dict to support dict() conversion like a neo4j.Record."""

    def __init__(self, data: dict):
        self._data = data

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key: str):
        return self._data[key]


class _FakeSession:
    def __init__(self, records: list[dict]):
        self._records = records

    async def run(self, query: str, **kwargs):
        return _FakeResult(self._records)


def _make_app(records: list[dict]) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.include_router(router, prefix="/api")

    session = _FakeSession(records)

    async def fake_graph_db():
        yield session

    test_app.dependency_overrides[get_graph_db] = fake_graph_db
    return test_app


class TestGraphEndpoint:
    async def test_returns_200(self):
        app = _make_app([FULL_RECORD])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/1234567890")
        assert resp.status_code == 200

    async def test_response_structure(self):
        app = _make_app([FULL_RECORD])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/1234567890")
        body = resp.json()
        assert "npi" in body
        assert "nodes" in body
        assert "edges" in body
        assert body["npi"] == "1234567890"

    async def test_node_count(self):
        app = _make_app([FULL_RECORD])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/1234567890")
        assert len(resp.json()["nodes"]) == 5

    async def test_edge_count(self):
        app = _make_app([FULL_RECORD])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/1234567890")
        assert len(resp.json()["edges"]) == 4

    async def test_404_when_not_found(self):
        empty_record = {
            "p": None,
            "hc": None,
            "c": None,
            "hs": None,
            "s": None,
            "ip": None,
            "pg": None,
            "sf": None,
            "src": None,
        }
        app = _make_app([empty_record])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/0000000000")
        assert resp.status_code == 404

    async def test_404_when_no_records(self):
        app = _make_app([])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/0000000000")
        assert resp.status_code == 404

    async def test_edge_types_correct(self):
        app = _make_app([FULL_RECORD])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/1234567890")
        edge_types = {e["type"] for e in resp.json()["edges"]}
        assert edge_types == {"HAS_CASE", "HAS_SIGNAL", "IN_PEER_GROUP", "SOURCED_FROM"}
