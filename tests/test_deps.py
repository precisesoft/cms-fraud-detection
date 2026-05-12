"""Tests for src/api/deps.py — async DB pool management."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_pool_globals():
    """Reset module-level pool globals before and after each test."""
    import src.api.deps as deps_mod

    original_pool = deps_mod.pool
    original_ro = deps_mod.readonly_pool
    deps_mod.pool = None
    deps_mod.readonly_pool = None
    yield
    deps_mod.pool = original_pool
    deps_mod.readonly_pool = original_ro


# ---------------------------------------------------------------------------
# open_pool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_pool_creates_both_pools() -> None:
    """open_pool initialises the read-write and read-only pools."""
    mock_pool = AsyncMock()
    mock_pool.open = AsyncMock()
    mock_pool.wait = AsyncMock()

    with patch("src.api.deps.AsyncConnectionPool", return_value=mock_pool) as ctor:
        from src.api.deps import open_pool

        result = await open_pool()

    assert result is mock_pool
    assert ctor.call_count == 2  # one RW, one RO


@pytest.mark.asyncio
async def test_open_pool_rw_params() -> None:
    """RW pool is created with min_size=2, max_size=10."""
    mock_pool = AsyncMock()

    with patch("src.api.deps.AsyncConnectionPool", return_value=mock_pool) as ctor:
        from src.api.deps import open_pool

        await open_pool()

    rw_call = ctor.call_args_list[0]
    assert rw_call.kwargs["min_size"] == 2
    assert rw_call.kwargs["max_size"] == 10


@pytest.mark.asyncio
async def test_open_pool_ro_params() -> None:
    """RO pool is created with min_size=1, max_size=5."""
    mock_pool = AsyncMock()

    with patch("src.api.deps.AsyncConnectionPool", return_value=mock_pool) as ctor:
        from src.api.deps import open_pool

        await open_pool()

    ro_call = ctor.call_args_list[1]
    assert ro_call.kwargs["min_size"] == 1
    assert ro_call.kwargs["max_size"] == 5


# ---------------------------------------------------------------------------
# close_pool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_pool_closes_both() -> None:
    """close_pool closes both pools and sets them to None."""
    import src.api.deps as deps_mod

    mock_rw = AsyncMock()
    mock_ro = AsyncMock()
    deps_mod.pool = mock_rw
    deps_mod.readonly_pool = mock_ro

    from src.api.deps import close_pool

    await close_pool()

    mock_rw.close.assert_awaited_once()
    mock_ro.close.assert_awaited_once()
    assert deps_mod.pool is None
    assert deps_mod.readonly_pool is None


@pytest.mark.asyncio
async def test_close_pool_when_already_none() -> None:
    """close_pool is safe to call when pools are already None."""
    from src.api.deps import close_pool

    await close_pool()  # should not raise


# ---------------------------------------------------------------------------
# get_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_raises_when_pool_none() -> None:
    """get_db raises RuntimeError if the pool is not initialised."""
    from src.api.deps import get_db

    gen = get_db()
    with pytest.raises(RuntimeError, match="pool not initialized"):
        await gen.__anext__()


@pytest.mark.asyncio
async def test_get_db_yields_connection() -> None:
    """get_db yields a connection from the pool."""
    import src.api.deps as deps_mod

    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_pool.connection.return_value = ctx
    deps_mod.pool = mock_pool

    from src.api.deps import get_db

    gen = get_db()
    conn = await gen.__anext__()
    assert conn is mock_conn


# ---------------------------------------------------------------------------
# get_readonly_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_readonly_db_raises_when_pool_none() -> None:
    """get_readonly_db raises RuntimeError if the readonly pool is not initialised."""
    from src.api.deps import get_readonly_db

    gen = get_readonly_db()
    with pytest.raises(RuntimeError, match="Readonly pool not initialized"):
        await gen.__anext__()


@pytest.mark.asyncio
async def test_get_readonly_db_yields_connection() -> None:
    """get_readonly_db yields a connection from the readonly pool."""
    import src.api.deps as deps_mod

    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_pool.connection.return_value = ctx
    deps_mod.readonly_pool = mock_pool

    from src.api.deps import get_readonly_db

    gen = get_readonly_db()
    conn = await gen.__anext__()
    assert conn is mock_conn


# ---------------------------------------------------------------------------
# DATABASE_URL defaults
# ---------------------------------------------------------------------------


def test_database_url_default_format() -> None:
    """DATABASE_URL falls back to a postgresql:// URL when env var is absent."""
    from src.api.deps import DATABASE_URL

    assert DATABASE_URL.startswith("postgresql://")


def test_readonly_url_default_format() -> None:
    """DATABASE_URL_READONLY falls back to a postgresql:// URL."""
    from src.api.deps import DATABASE_URL_READONLY

    assert DATABASE_URL_READONLY.startswith("postgresql://")


def test_readonly_url_defaults_to_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Readonly URL falls back to DATABASE_URL when no explicit readonly URL exists."""
    import src.api.deps as deps_mod

    monkeypatch.setenv("DATABASE_URL", "postgresql://cms:test@db:5432/cms_fraud")
    monkeypatch.delenv("DATABASE_URL_READONLY", raising=False)

    reloaded = importlib.reload(deps_mod)

    assert reloaded.DATABASE_URL_READONLY == reloaded.DATABASE_URL

    monkeypatch.undo()
    importlib.reload(reloaded)
