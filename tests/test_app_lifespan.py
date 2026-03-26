"""Tests for src/api/app.py — FastAPI app factory and lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI


def _mock_pool_with_connection():
    """Build a mock pool whose .connection() yields an async context manager."""
    mock_conn = AsyncMock()

    @asynccontextmanager
    async def _connection():
        yield mock_conn

    mock_pool = AsyncMock()
    mock_pool.connection = _connection
    return mock_pool


# Shared patch targets — lifespan binds at import time on src.api.app
_LIFESPAN_PATCHES = {
    "src.api.app.open_pool": AsyncMock(),
    "src.api.app.close_pool": AsyncMock(),
    "src.api.app.open_neo4j": AsyncMock(),
    "src.api.app.close_neo4j": AsyncMock(),
    "src.api.app.stop_queue": AsyncMock(),
}


# ---------------------------------------------------------------------------
# App factory basics
# ---------------------------------------------------------------------------


def test_create_app_returns_fastapi() -> None:
    """create_app returns a FastAPI instance."""
    from src.api.app import create_app

    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_title_and_version() -> None:
    """App has correct title and version metadata."""
    from src.api.app import create_app

    app = create_app()
    assert app.title == "CMS Fraud Detection API"
    assert app.version == "0.1.0"


def test_all_api_routes_have_prefix() -> None:
    """All registered routes (except /health and framework routes) start with /api."""
    from src.api.app import create_app

    app = create_app()
    framework_paths = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    ops_paths = {"/health", "/healthz"}
    paths = [
        r.path
        for r in app.routes
        if hasattr(r, "path") and r.path not in framework_paths and r.path not in ops_paths
    ]
    for path in paths:
        assert path.startswith("/api"), f"Route {path} does not start with /api"


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthz_returns_ok_immediately() -> None:
    """Lightweight /healthz responds instantly with no dependencies."""
    with patch.multiple(
        "src.api.app", **{k.split(".")[-1]: AsyncMock() for k in _LIFESPAN_PATCHES}
    ):
        from src.api.app import create_app

        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/healthz")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_both_ok() -> None:
    """Health returns ok for database and graph when both are available."""
    mock_pool = _mock_pool_with_connection()
    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock()

    with (
        patch.multiple("src.api.app", **{k.split(".")[-1]: AsyncMock() for k in _LIFESPAN_PATCHES}),
        patch("src.api.deps.pool", mock_pool),
        patch("src.api.graph_client.driver", mock_driver),
    ):
        from src.api.app import create_app

        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["graph"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_database_unavailable() -> None:
    """Health returns database=unavailable when pool is None."""
    with (
        patch.multiple("src.api.app", **{k.split(".")[-1]: AsyncMock() for k in _LIFESPAN_PATCHES}),
        patch("src.api.deps.pool", None),
        patch("src.api.graph_client.driver", None),
    ):
        from src.api.app import create_app

        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")

    data = resp.json()
    assert data["database"] == "unavailable"
    assert data["graph"] == "unavailable"


@pytest.mark.asyncio
async def test_health_graph_unavailable_db_ok() -> None:
    """Health returns graph=unavailable when Neo4j driver is None but DB is ok."""
    mock_pool = _mock_pool_with_connection()

    with (
        patch.multiple("src.api.app", **{k.split(".")[-1]: AsyncMock() for k in _LIFESPAN_PATCHES}),
        patch("src.api.deps.pool", mock_pool),
        patch("src.api.graph_client.driver", None),
    ):
        from src.api.app import create_app

        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")

    data = resp.json()
    assert data["database"] == "ok"
    assert data["graph"] == "unavailable"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cors_headers_present() -> None:
    """CORS middleware sets access-control-allow-origin on responses."""
    with (
        patch.multiple("src.api.app", **{k.split(".")[-1]: AsyncMock() for k in _LIFESPAN_PATCHES}),
        patch("src.api.deps.pool", None),
        patch("src.api.graph_client.driver", None),
    ):
        from src.api.app import create_app

        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health", headers={"Origin": "http://localhost:3000"})

    origin = resp.headers.get("access-control-allow-origin")
    assert origin is not None, "CORS header missing — middleware not applied"


# ---------------------------------------------------------------------------
# Lifespan — Neo4j graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifespan_neo4j_failure_does_not_block_startup() -> None:
    """If Neo4j fails during startup, the lifespan still completes (no raise)."""
    from src.api.app import lifespan

    mock_open_pool = AsyncMock()
    mock_open_neo4j = AsyncMock(side_effect=ConnectionRefusedError("Neo4j down"))
    mock_app = AsyncMock()

    with (
        patch("src.api.app.open_pool", mock_open_pool),
        patch("src.api.app.close_pool", AsyncMock()),
        patch("src.api.app.open_neo4j", mock_open_neo4j),
        patch("src.api.app.close_neo4j", AsyncMock()),
        patch("src.api.app.stop_queue", AsyncMock()),
    ):
        async with lifespan(mock_app):
            pass  # startup succeeded despite Neo4j failure

    mock_open_pool.assert_awaited_once()
    mock_open_neo4j.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_calls_open_and_close() -> None:
    """Lifespan opens dependencies and closes cleanly."""
    from src.api.app import lifespan

    mock_open = AsyncMock()
    mock_close = AsyncMock()
    mock_neo_open = AsyncMock()
    mock_neo_close = AsyncMock()
    mock_stop_queue = AsyncMock()
    mock_app = AsyncMock()

    with (
        patch("src.api.app.open_pool", mock_open),
        patch("src.api.app.close_pool", mock_close),
        patch("src.api.app.open_neo4j", mock_neo_open),
        patch("src.api.app.close_neo4j", mock_neo_close),
        patch("src.api.app.stop_queue", mock_stop_queue),
    ):
        async with lifespan(mock_app):
            pass

    mock_open.assert_awaited_once()
    mock_close.assert_awaited_once()
    mock_neo_open.assert_awaited_once()
    mock_neo_close.assert_awaited_once()
    mock_stop_queue.assert_awaited_once()
