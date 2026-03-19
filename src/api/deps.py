"""Database connection pool and FastAPI dependencies."""

from __future__ import annotations

import os

from psycopg_pool import AsyncConnectionPool

FORGE_HOST = "172.16.0.191"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql://cms:cms_local_dev@{FORGE_HOST}:30432/cms_fraud",
)
DATABASE_URL_READONLY = os.environ.get(
    "DATABASE_URL_READONLY",
    f"postgresql://cms_readonly:cms_readonly_dev@{FORGE_HOST}:30432/cms_fraud",
)

pool: AsyncConnectionPool | None = None
readonly_pool: AsyncConnectionPool | None = None


async def open_pool() -> AsyncConnectionPool:
    global pool, readonly_pool
    pool = AsyncConnectionPool(conninfo=DATABASE_URL, min_size=2, max_size=10, open=False)
    await pool.open()
    await pool.wait()
    readonly_pool = AsyncConnectionPool(
        conninfo=DATABASE_URL_READONLY, min_size=1, max_size=5, open=False
    )
    await readonly_pool.open()
    await readonly_pool.wait()
    return pool


async def close_pool() -> None:
    global pool, readonly_pool
    if readonly_pool:
        await readonly_pool.close()
        readonly_pool = None
    if pool:
        await pool.close()
        pool = None


async def get_db():
    """FastAPI dependency — yields an async connection from the pool."""
    if pool is None:
        raise RuntimeError("Database pool not initialized — app lifespan not started")
    async with pool.connection() as conn:
        yield conn


async def get_readonly_db():
    """FastAPI dependency — yields a READ-ONLY connection for AI chat queries."""
    if readonly_pool is None:
        raise RuntimeError("Readonly pool not initialized — app lifespan not started")
    async with readonly_pool.connection() as conn:
        yield conn
