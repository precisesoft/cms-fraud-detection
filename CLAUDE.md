# CMS Fraud Detection - Claude Instructions

## SDLC — MANDATORY

Follow CONTRIBUTING.md for all code changes. Key rules:

1. **Never commit to main.** Always: branch → PR → CI green → review → merge.
2. **One issue at a time.** Label it `in-progress`, create branch `<type>/<N>-<desc>`.
3. **Run CI locally before pushing:**
   ```bash
   ruff check src/ tests/ && ruff format --check src/ tests/
   mypy src/
   pytest --cov=src --cov-report=term -q
   ```
4. **Conventional commits:** `type(scope): description (#N)`
5. **PR must include** `Closes #N` in body.
6. **Self-validate (BASSPC) before presenting PR** — never skip this.
7. **After merge:** verify issue closed, comment PR# on issue, update parent epic (mark CLOSED with PR#), remove `in-progress` label, `git checkout main && git pull`.
8. **Watch CI in background** — don't flood context with `gh run watch` output.

## Project Overview

Proactive CMS provider fraud detection with explainable AI. Identifies anomalous Medicare billing patterns using peer comparison, risk scoring, and AI-generated narratives.

## Architecture

- **API:** FastAPI with async psycopg pool (`src/api/`)
- **Scoring:** Deterministic rule engine + Isolation Forest (`src/scoring/`, `src/models/`)
- **AI:** AWS Bedrock Claude — text-to-SQL, narratives, chat (`src/ai/`)
- **Pipeline:** Polars-based feature engineering (`src/pipeline/`)
- **Data:** psycopg COPY bulk loader, Neo4j projection (`src/data/`)
- **Validation:** Retrospective scoring vs. revocation outcomes (`src/validation/`)
- **DB:** PostgreSQL 16 + Neo4j 5 on EKS (namespace: `cms-fraud`)
- **Frontend:** Vite + React 19 + React Router + Tailwind v4 (`frontend/`)
- **Schemas:** Pydantic v2 models (`src/api/schemas.py`)

## Key Files

| Path                              | Purpose                                        |
| --------------------------------- | ---------------------------------------------- |
| `src/api/app.py`                  | FastAPI app factory with lifespan              |
| `src/api/deps.py`                 | DB pool management, FastAPI deps               |
| `src/api/schemas.py`              | All Pydantic request/response models           |
| `src/api/routes/`                 | 14 route modules (dashboard, score, chat, ...) |
| `src/scoring/taxonomy.py`         | Signal definitions, weights, thresholds        |
| `src/scoring/extract.py`          | Signal extraction per case                     |
| `src/scoring/score.py`            | Risk + legitimacy score computation            |
| `src/ai/text_to_sql.py`           | NL → PostgreSQL SQL                            |
| `src/ai/narrative.py`             | Structured signals → narrative                 |
| `src/models/anomaly_scorer.py`    | Isolation Forest inference                     |
| `src/validation/retrospective.py` | Retrospective validation                       |
| `src/pipeline/build_features.py`  | Provider-level feature engineering             |
| `src/data/load_postgres.py`       | Bulk data loader                               |
| `frontend/src/App.tsx`            | React Router route definitions                 |
| `frontend/src/pages/`             | All page components (Dashboard, Simulate, ...) |
| `pyproject.toml`                  | Deps, ruff, mypy, bandit, pytest config        |

## CI/CD (unified pipeline)

| Workflow        | Jobs                                                                                                                                                                                                                                      |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pipeline.yml`  | Gate (PR title) → Security (gitleaks, bandit, pip-audit, npm audit) → Quality Backend (ruff, mypy, pytest 80%) → Quality Frontend (eslint, tsc, vitest 80%, build) → Build (Docker + SBOM) → Scan (Trivy) → Release + Deploy (merge only) |
| `terraform.yml` | Plan on PR, apply on merge (paths: terraform/\*\*)                                                                                                                                                                                        |

## Conventions

- **Git:** conventional commits, present tense, `(#N)` suffix
- **Python:** 3.12+, ruff for lint/format, mypy for types
- **Naming:** kebab-case dirs/files, PascalCase classes, snake_case functions
- **Risk bands:** 0-25 stable, 26-50 review, 51+ high_risk
- **DB creds:** dev default `cms:cms_local_dev` — never use in production

## Completed Epics

- **Epic #8:** CI/CD Pipeline v1 — COMPLETE
- **Epic #112:** EKS Migration — COMPLETE
- **Epic #273:** Unified CI/CD Pipeline — COMPLETE
- **Epic #302:** Test Coverage 90%+ — COMPLETE (99% backend, 98% frontend)
