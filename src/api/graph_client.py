"""Neo4j async driver wrapper and FastAPI dependency."""

from __future__ import annotations

import os

from neo4j import AsyncDriver, AsyncGraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "cms_graph_dev")

driver: AsyncDriver | None = None


async def open_neo4j() -> AsyncDriver:
    """Create and verify the async Neo4j driver."""
    global driver
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    await driver.verify_connectivity()
    return driver


async def close_neo4j() -> None:
    """Close the Neo4j driver."""
    global driver
    if driver:
        await driver.close()
        driver = None


async def get_graph_db():
    """FastAPI dependency — yields an async Neo4j session."""
    if driver is None:
        raise RuntimeError("Neo4j driver not initialized — app lifespan not started")
    async with driver.session() as session:
        yield session
