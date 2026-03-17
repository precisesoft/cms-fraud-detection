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
7. **After merge:** verify issue closed, update parent epic, `git checkout main && git pull`.
8. **Watch CI in background** — don't flood context with `gh run watch` output.

## Project Overview

Proactive CMS provider fraud detection with explainable AI. Identifies anomalous Medicare billing patterns using peer comparison, risk scoring, and AI-generated narratives.

## Architecture

- **API:** FastAPI with async psycopg pool (`src/api/`)
- **Pipeline:** Polars-based feature engineering (`src/pipeline/`)
- **Data:** psycopg COPY bulk loader (`src/data/`)
- **DB:** PostgreSQL 16 on forge k3s (NodePort 30432)
- **Schemas:** Pydantic v2 models (`src/api/schemas.py`)

## Key Files

| Path                             | Purpose                                 |
| -------------------------------- | --------------------------------------- |
| `src/api/app.py`                 | FastAPI app factory with lifespan       |
| `src/api/deps.py`                | DB pool management, FastAPI deps        |
| `src/api/schemas.py`             | All Pydantic request/response models    |
| `src/pipeline/build_features.py` | Provider-level feature engineering      |
| `src/data/load_postgres.py`      | Bulk data loader                        |
| `tests/test_build_features.py`   | Feature pipeline tests                  |
| `pyproject.toml`                 | Deps, ruff, mypy, bandit, pytest config |

## CI Checks (all must pass on PRs)

| Workflow       | Jobs                                                    |
| -------------- | ------------------------------------------------------- |
| `ci.yml`       | lint (ruff), typecheck (mypy), test (pytest + coverage) |
| `secrets.yml`  | gitleaks secrets scan                                   |
| `security.yml` | pip-audit (CVEs), bandit (SAST)                         |

## Conventions

- **Git:** conventional commits, present tense, `(#N)` suffix
- **Python:** 3.12+, ruff for lint/format, mypy for types
- **Naming:** kebab-case dirs/files, PascalCase classes, snake_case functions
- **Risk bands:** 0-30 stable, 31-50 review, 51+ high_risk
- **DB creds:** dev default `cms:cms_local_dev` — never use in production

## Active Epics

- **Epic #8:** CI/CD Pipeline — see issue for child issues and status
