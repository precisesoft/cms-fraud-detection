"""Project evidence graph from PostgreSQL into Neo4j.

Reads provider_features and provider_service_cases from Postgres, creates
nodes (Provider, Case, Signal, PeerGroup, Source) and relationships
(HAS_CASE, HAS_SIGNAL, IN_PEER_GROUP, SOURCED_FROM) in Neo4j.

Usage:
    python -m src.data.project_graph
"""

from __future__ import annotations

import asyncio
import logging
import os

import psycopg
from neo4j import AsyncDriver, AsyncGraphDatabase

from src.scoring.extract import extract_signals
from src.scoring.taxonomy import ALL_SIGNALS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://cms:cms_local_dev@172.16.0.191:30432/cms_fraud",
)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "cms_graph_dev")

BATCH_SIZE = 500

# ---------------------------------------------------------------------------
# Data sources (static reference nodes)
# ---------------------------------------------------------------------------

SOURCES = [
    {
        "dataset": "Medicare Physician & Other Practitioners",
        "year": "2022",
        "url": "https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service",
    },
    {
        "dataset": "Medicare Fee-for-Service Public Provider Enrollment",
        "year": "2025",
        "url": "https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/medicare-fee-for-service-public-provider-enrollment",
    },
    {
        "dataset": "CMS Provider Revocation File",
        "year": "2026",
        "url": "https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/revoked-medicare-providers",
    },
]

# Map signal categories to their source datasets
_SIGNAL_SOURCE_MAP = {
    "enrollment": "Medicare Fee-for-Service Public Provider Enrollment",
    "volume": "Medicare Physician & Other Practitioners",
    "charge": "Medicare Physician & Other Practitioners",
    "peer": "Medicare Physician & Other Practitioners",
}


# ---------------------------------------------------------------------------
# Cypher templates
# ---------------------------------------------------------------------------

_CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Provider) REQUIRE p.npi IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.case_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Signal) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pg:PeerGroup) REQUIRE pg.key IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (src:Source) REQUIRE src.dataset IS UNIQUE",
]

_MERGE_SOURCES = """
UNWIND $rows AS r
MERGE (s:Source {dataset: r.dataset})
SET s.year = r.year, s.url = r.url
"""

_MERGE_SIGNALS = """
UNWIND $rows AS r
MERGE (s:Signal {name: r.name})
SET s.category = r.category, s.direction = r.direction,
    s.description = r.description, s.points = r.points
"""

_LINK_SIGNAL_SOURCE = """
UNWIND $rows AS r
MATCH (sig:Signal {name: r.signal_name})
MATCH (src:Source {dataset: r.source_dataset})
MERGE (sig)-[:SOURCED_FROM]->(src)
"""

_MERGE_PROVIDERS = """
UNWIND $rows AS r
MERGE (p:Provider {npi: r.npi})
SET p.name = r.name, p.type = r.type, p.state = r.state,
    p.risk_score = r.risk_score, p.risk_band = r.risk_band,
    p.enrolled = r.enrolled, p.revoked = r.revoked
"""

_MERGE_CASES = """
UNWIND $rows AS r
MERGE (c:Case {case_id: r.case_id})
SET c.hcpcs_cd = r.hcpcs_cd, c.risk_score = r.risk_score,
    c.legitimacy_score = r.legitimacy_score, c.label = r.label
WITH c, r
MATCH (p:Provider {npi: r.npi})
MERGE (p)-[:HAS_CASE]->(c)
"""

_MERGE_PEER_GROUP = """
UNWIND $rows AS r
MERGE (pg:PeerGroup {key: r.key})
SET pg.specialty = r.specialty, pg.hcpcs_cd = r.hcpcs_cd,
    pg.count = r.count, pg.scope = r.scope
WITH pg, r
MATCH (c:Case {case_id: r.case_id})
MERGE (c)-[:IN_PEER_GROUP]->(pg)
"""

_MERGE_CASE_SIGNALS = """
UNWIND $rows AS r
MATCH (c:Case {case_id: r.case_id})
MATCH (s:Signal {name: r.signal_name})
MERGE (c)-[rel:HAS_SIGNAL]->(s)
SET rel.value = r.value, rel.points = r.points
"""


# ---------------------------------------------------------------------------
# Projection functions
# ---------------------------------------------------------------------------


def _risk_band(score: int | None) -> str:
    if score is None:
        return "stable"
    if score >= 51:
        return "high_risk"
    if score >= 31:
        return "review"
    return "stable"


async def _create_constraints(driver: AsyncDriver) -> None:
    async with driver.session() as session:
        for cypher in _CREATE_CONSTRAINTS:
            await session.run(cypher)
    log.info("Created %d constraints", len(_CREATE_CONSTRAINTS))


async def _project_sources(driver: AsyncDriver) -> None:
    async with driver.session() as session:
        await session.run(_MERGE_SOURCES, rows=SOURCES)
    log.info("Projected %d Source nodes", len(SOURCES))


async def _project_signals(driver: AsyncDriver) -> None:
    signal_rows = [
        {
            "name": s.name,
            "category": s.category.value,
            "direction": s.direction.value,
            "description": s.description,
            "points": s.points if s.points else (s.z_tiers[0].points if s.z_tiers else 0),
        }
        for s in ALL_SIGNALS
    ]
    link_rows = [
        {
            "signal_name": s.name,
            "source_dataset": _SIGNAL_SOURCE_MAP.get(s.category.value, ""),
        }
        for s in ALL_SIGNALS
    ]
    # Special case: revoked_provider links to the revocation file
    for row in link_rows:
        if row["signal_name"] == "revoked_provider":
            row["source_dataset"] = "CMS Provider Revocation File"

    async with driver.session() as session:
        await session.run(_MERGE_SIGNALS, rows=signal_rows)
        await session.run(_LINK_SIGNAL_SOURCE, rows=link_rows)
    log.info("Projected %d Signal nodes with SOURCED_FROM links", len(signal_rows))


async def _project_providers(driver: AsyncDriver, pg_conninfo: str) -> int:
    count = 0
    async with await psycopg.AsyncConnection.connect(pg_conninfo) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT npi, provider_name, provider_type, state, "
                "max_seed_risk_score, enrolled_2025, revoked_2026 "
                "FROM provider_features"
            )
            batch: list[dict] = []
            async for row in cur:
                batch.append(
                    {
                        "npi": row[0],
                        "name": row[1],
                        "type": row[2],
                        "state": row[3],
                        "risk_score": row[4],
                        "risk_band": _risk_band(row[4]),
                        "enrolled": bool(row[5]),
                        "revoked": bool(row[6]),
                    }
                )
                if len(batch) >= BATCH_SIZE:
                    async with driver.session() as session:
                        await session.run(_MERGE_PROVIDERS, rows=batch)
                    count += len(batch)
                    batch = []
            if batch:
                async with driver.session() as session:
                    await session.run(_MERGE_PROVIDERS, rows=batch)
                count += len(batch)
    log.info("Projected %d Provider nodes", count)
    return count


async def _project_cases_and_signals(driver: AsyncDriver, pg_conninfo: str) -> int:
    count = 0
    async with await psycopg.AsyncConnection.connect(pg_conninfo) as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("SELECT * FROM provider_service_cases")
            case_batch: list[dict] = []
            peer_batch: list[dict] = []
            signal_batch: list[dict] = []
            async for row in cur:
                case_batch.append(
                    {
                        "case_id": row["case_id"],
                        "npi": row["npi"],
                        "hcpcs_cd": row["hcpcs_cd"],
                        "risk_score": row.get("seed_risk_score", 0),
                        "legitimacy_score": row.get("seed_legitimacy_score", 0),
                        "label": row.get("seed_case_label", "review"),
                    }
                )
                # Peer group
                peer_count = row.get("peer_case_count") or 0
                if peer_count > 0 and row.get("peer_scope"):
                    key = f"{row['provider_type']}|{row['hcpcs_cd']}|{row['peer_scope']}"
                    peer_batch.append(
                        {
                            "case_id": row["case_id"],
                            "key": key,
                            "specialty": row.get("provider_type", ""),
                            "hcpcs_cd": row["hcpcs_cd"],
                            "count": peer_count,
                            "scope": row.get("peer_scope", ""),
                        }
                    )
                # Signals
                fired = extract_signals(row)
                for fs in fired:
                    signal_batch.append(
                        {
                            "case_id": row["case_id"],
                            "signal_name": fs.signal.name,
                            "value": fs.value,
                            "points": fs.points,
                        }
                    )

                if len(case_batch) >= BATCH_SIZE:
                    async with driver.session() as session:
                        await session.run(_MERGE_CASES, rows=case_batch)
                        if peer_batch:
                            await session.run(_MERGE_PEER_GROUP, rows=peer_batch)
                        if signal_batch:
                            await session.run(_MERGE_CASE_SIGNALS, rows=signal_batch)
                    count += len(case_batch)
                    log.info("Projected %d cases so far...", count)
                    case_batch, peer_batch, signal_batch = [], [], []

            if case_batch:
                async with driver.session() as session:
                    await session.run(_MERGE_CASES, rows=case_batch)
                    if peer_batch:
                        await session.run(_MERGE_PEER_GROUP, rows=peer_batch)
                    if signal_batch:
                        await session.run(_MERGE_CASE_SIGNALS, rows=signal_batch)
                count += len(case_batch)
    log.info("Projected %d Case nodes with signals and peer groups", count)
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run_projection(
    pg_conninfo: str = DATABASE_URL,
    neo4j_uri: str = NEO4J_URI,
    neo4j_user: str = NEO4J_USER,
    neo4j_password: str = NEO4J_PASSWORD,
) -> dict[str, int]:
    """Run the full PostgreSQL → Neo4j projection. Returns node counts."""
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        await driver.verify_connectivity()
        log.info("Connected to Neo4j at %s", neo4j_uri)

        await _create_constraints(driver)
        await _project_sources(driver)
        await _project_signals(driver)
        provider_count = await _project_providers(driver, pg_conninfo)
        case_count = await _project_cases_and_signals(driver, pg_conninfo)

        return {"providers": provider_count, "cases": case_count}
    finally:
        await driver.close()


def main() -> None:
    counts = asyncio.run(run_projection())
    log.info("Projection complete: %s", counts)


if __name__ == "__main__":
    main()
