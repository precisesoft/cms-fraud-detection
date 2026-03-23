# Copilot Instructions — CMS Fraud Detection (Argus)

## Project

Proactive CMS provider fraud detection with explainable AI. Identifies anomalous Medicare billing patterns using peer comparison, risk scoring, and AI-generated narratives.

## Stack

- **API**: FastAPI + async psycopg pool (`src/api/`)
- **Pipeline**: Polars-based feature engineering (`src/pipeline/`)
- **AI Layer**: AWS Bedrock Claude for text-to-SQL and risk narratives (`src/ai/`)
- **DB**: PostgreSQL 16 (provider_features: 63 columns, provider_service_cases: case-level)
- **Graph**: Neo4j 5 for network risk signals
- **Frontend**: Vite + React 19 + React Router + Tailwind v4 + Recharts
- **Python**: 3.12+, type-checked with mypy, linted with ruff

## Conventions

- **Commits**: `type(scope): description (#N)` — conventional commits, present tense. `#N` MUST be the real GitHub issue number, never a placeholder like `#issue`. Example: `docs: update README (#42)`
- **Branches**: `<type>/<issue-number>-<description>`
- **PRs**: Title MUST follow conventional commit format from the very first push: `type(scope): description (#N)`. Body must include `Closes #N`. Do not use redundant scopes (e.g., use `docs:` not `docs(docs):`). NEVER use `[WIP]` prefix — it fails the CI Gate check.
- **Risk bands**: 0-30 stable, 31-50 review, 51+ high_risk (use StrEnum `RiskBand`)
- **Naming**: kebab-case dirs/files, PascalCase classes, snake_case functions
- **Tests**: pytest + pytest-asyncio, `asyncio_mode = "auto"`

## Code Style

- Pydantic v2 models for all API schemas (`src/api/schemas.py`)
- Use `polars` for dataframes, never pandas
- SQL queries use parameterized `$1` placeholders (psycopg), never f-strings
- Async everywhere in the API layer — no sync DB calls
- Keep functions focused; prefer flat logic over deep nesting

## Security

- Text-to-SQL has guardrails: block UNION, subqueries, pg_sleep, comments
- All user inputs validated via Pydantic before reaching DB
- No hardcoded credentials — use environment variables
- Healthcare data context: treat all provider/claims data as sensitive

## Testing

- Run full CI locally: `ruff check`, `ruff format --check`, `mypy src/`, `pytest`
- Tests use in-memory mocks, not live DB connections
- Coverage target: maintain or improve current coverage
- Use `pytest.mark.asyncio` for async test functions

## What NOT to Do

- Do not add pandas as a dependency
- Do not use `type: ignore` — fix the type error or use TypedDict
- Do not modify `db/init.sql` without considering migration impact
- Do not commit directly to main
