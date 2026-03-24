"""Tests for src/api/graph_client module."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

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

    async def test_yields_session_when_driver_initialized(self):
        """get_graph_db yields a session from driver.session()."""
        mock_session = AsyncMock()

        @asynccontextmanager
        async def _fake_session():
            yield mock_session

        mock_driver = MagicMock()
        mock_driver.session = _fake_session

        original = graph_client.driver
        graph_client.driver = mock_driver
        try:
            gen = graph_client.get_graph_db()
            session = await gen.__anext__()
            assert session is mock_session
            # exhaust the generator (covers the cleanup/exit path)
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
        finally:
            graph_client.driver = original


class TestCloseNeo4j:
    async def test_close_when_no_driver(self):
        """close_neo4j is safe to call when driver is None."""
        graph_client.driver = None
        await graph_client.close_neo4j()
        assert graph_client.driver is None

    async def test_close_calls_driver_close_and_nils_ref(self):
        """close_neo4j closes an active driver and sets module-level ref to None."""
        mock_driver = AsyncMock()
        original = graph_client.driver
        graph_client.driver = mock_driver
        try:
            await graph_client.close_neo4j()
            mock_driver.close.assert_awaited_once()
            assert graph_client.driver is None
        finally:
            graph_client.driver = original


class TestOpenNeo4j:
    async def test_open_creates_driver_and_verifies_connectivity(self):
        """open_neo4j creates an AsyncGraphDatabase driver and calls verify_connectivity."""
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()

        original = graph_client.driver
        try:
            with patch(
                "src.api.graph_client.AsyncGraphDatabase.driver",
                return_value=mock_driver,
            ) as mock_factory:
                result = await graph_client.open_neo4j()

            mock_factory.assert_called_once_with(
                graph_client.NEO4J_URI,
                auth=(graph_client.NEO4J_USER, graph_client.NEO4J_PASSWORD),
            )
            mock_driver.verify_connectivity.assert_awaited_once()
            assert result is mock_driver
            assert graph_client.driver is mock_driver
        finally:
            graph_client.driver = original
