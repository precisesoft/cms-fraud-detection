# Sprint Scoreboard — 2026-03-16

**Target**: CMS AI Hackathon demo — March 27, 2026 (11 days remaining)

## Summary

Phase 0 (Spine) and Phase 1 (Data Foundation) are effectively complete. Phase 2 (Scoring Engine + API) is in progress — the FastAPI server, Pydantic schemas, async DB pool, and health endpoint are live. Postgres is deployed and healthy on forge k3s. All 17 unit tests pass. The critical path now runs through the API endpoints (#36, #37, #38) which unblock the entire frontend.

## Scoreboard

| Phase                   | Closed | Open   | % Done  | Status                           |
| ----------------------- | ------ | ------ | ------- | -------------------------------- |
| 0: Spine                | 1      | 0      | 100%    | Done                             |
| 1: Data Foundation      | 7      | 2      | 78%     | Neo4j + ETL test remaining       |
| 2: Scoring Engine + API | 2      | 10     | 17%     | In progress — API endpoints next |
| 3: AI Intelligence      | 0      | 7      | 0%      | Blocked on API + Bedrock setup   |
| 4: UI                   | 0      | 16     | 0%      | Blocked on API endpoints         |
| 5: Ship                 | 1      | 8      | 11%     | Docs can start in parallel       |
| Infra (CI/CD)           | 0      | 4      | 0%      | Deferred                         |
| **Total**               | **11** | **59** | **16%** |                                  |

## Closed Issues (11)

| #   | Title                               | Phase    |
| --- | ----------------------------------- | -------- |
| 15  | Create PostgreSQL schema            | 1: Data  |
| 16  | Build DuckDB ingestion pipeline     | 1: Data  |
| 17  | Build provider identity spine       | 1: Data  |
| 18  | Compute peer baselines              | 1: Data  |
| 19  | Harvest signals and compute scores  | 1: Data  |
| 20  | Bulk load Parquet into PostgreSQL   | 1: Data  |
| 35  | FastAPI app factory with middleware | 2: API   |
| 40  | Pydantic schemas for all API models | 2: API   |
| 54  | Generate architecture diagram       | 5: Ship  |
| 67  | Create demo data fixture            | 1: Data  |
| 68  | Environment setup + docker-compose  | 0: Spine |

## What Shipped Today

- **Pydantic schemas** (`src/api/schemas.py`) — 15 models covering providers, claims, scoring, dashboard, heatmap, fairness, and chat. All 63 DB columns mapped.
- **FastAPI app factory** (`src/api/app.py`) — async lifespan, CORS, `GET /health` with live DB check.
- **Async DB pool** (`src/api/deps.py`) — psycopg-pool `AsyncConnectionPool`, `get_db()` dependency.
- **Dependency** — added `psycopg-pool>=3.2` to pyproject.toml.
- All validated: ruff clean, 17 tests pass, health endpoint returns `{"database": "ok"}`.

## Infrastructure Status

| Resource             | Status                     |
| -------------------- | -------------------------- |
| Postgres (forge k3s) | Running, Ready, 0 restarts |
| PVC (5Gi)            | Bound                      |
| Service              | NodePort 5432:30432        |
| API server (local)   | Verified via uvicorn       |

## Next Steps (Priority Order)

| Issue    | Title                                     | Why                                                        |
| -------- | ----------------------------------------- | ---------------------------------------------------------- |
| #36      | `/api/providers` + `/api/providers/{npi}` | Core data endpoint — dashboard + detail panel depend on it |
| #37      | `/api/claims` with pagination             | Claims table UI depends on it                              |
| #38      | `/api/score` endpoint                     | Live scoring demo moment                                   |
| #41      | Scaffold Next.js frontend                 | Unblocks all Phase 4 UI work                               |
| #55, #56 | Scoring methodology + responsible AI docs | Can parallelize with UI work                               |

## Risks

- **kubectl broken from megamind** — Go TLS issue. Workaround: direct curl with certs. Not blocking development.
- **59 open issues, 11 days** — Must ruthlessly prioritize P0 items for demo. P2 items (#21 Neo4j, #51 starter questions, #66 graph viz) are cut candidates.
- **No frontend scaffold yet** — Phase 4 is 0%. API endpoints must ship fast to give UI enough runway.
