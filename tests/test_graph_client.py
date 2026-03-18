"""Tests for src/api/graph_client module."""

from __future__ import annotations

import pytest

from src.api import graph_client


class TestGraphClientConfig:
    def test_default_uri(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("NEO4J_URI", raising=False)
        # Re-import to pick up default
        assert graph_client.NEO4J_URI is not None

    def test_default_password(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        assert graph_client.NEO4J_PASSWORD is not None


class TestGetGraphDb:
    async def test_raises_when_driver_not_initialized(self):
        original = graph_client.driver
        graph_client.driver = None
        try:
            gen = graph_client.get_graph_db()
            with pytest.raises(RuntimeError, match="Neo4j driver not initialized"):
                await gen.__anext__()
        finally:
            graph_client.driver = original


class TestCloseNeo4j:
    async def test_close_when_no_driver(self):
        """close_neo4j is safe to call when driver is None."""
        graph_client.driver = None
        await graph_client.close_neo4j()
        assert graph_client.driver is None
