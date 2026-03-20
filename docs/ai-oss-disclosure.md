# AI Tool & Open-Source Disclosure

This document inventories the AI tools and open-source libraries used in the CMS Fraud Detection system, in accordance with hackathon competition rules that require explicit disclosure of third-party AI and software components.

## AI Tools

### AWS Bedrock — Claude (Anthropic)

| Model | Identifier | Usage |
|---|---|---|
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Text-to-SQL: translates analyst natural-language questions into validated PostgreSQL queries (`POST /api/chat`) |
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` | Risk narratives: generates plain-language investigation briefs from structured scoring data (`POST /api/score`, `POST /api/claims/simulate`) |

All Claude invocations are routed through AWS Bedrock. No Anthropic API keys are used directly. Model IDs are overridable via environment variables (`BEDROCK_CHAT_MODEL`, `BEDROCK_NARRATIVE_MODEL`).

**Scope of AI use**: AI-generated content is advisory only. Risk scores, case labels, and all enforcement-relevant outputs are computed by deterministic, rule-based logic with no AI involvement. See [Responsible AI Considerations](./responsible-ai-considerations.md) for full details.

### Claude for Development (Anthropic)

Claude was used as a development assistant during the hackathon to accelerate coding, code review, and documentation tasks. All AI-assisted output was reviewed, tested, and validated by human team members before merging.

## Open-Source Libraries

### Backend (Python)

| Library | Version | License | Purpose |
|---|---|---|---|
| FastAPI | ≥0.115 | MIT | Async REST API framework |
| Uvicorn | ≥0.30 | BSD-3-Clause | ASGI server |
| Pydantic | ≥2.0 | MIT | Request/response schema validation |
| psycopg | ≥3.2 | LGPL-3.0 | Async PostgreSQL driver |
| psycopg-pool | ≥3.2 | LGPL-3.0 | PostgreSQL connection pooling |
| Polars | ≥1.0 | MIT | Dataframe-based feature engineering pipeline |
| PyArrow | ≥17.0 | Apache-2.0 | Columnar data serialization |
| boto3 | ≥1.35 | Apache-2.0 | AWS SDK for Bedrock invocations |
| neo4j | ≥5.0 | Apache-2.0 | Neo4j graph database driver |
| httpx | ≥0.27 | BSD-3-Clause | Async HTTP client |

### Frontend (JavaScript / TypeScript)

| Library | Version | License | Purpose |
|---|---|---|---|
| Next.js | 16.2.0 | MIT | React framework with App Router |
| React | 19.2.4 | MIT | UI component library |
| Tailwind CSS | ≥4.2 | MIT | Utility-first CSS framework |
| shadcn/ui | ≥4.0 | MIT | Accessible component primitives |
| Recharts | ≥3.8 | MIT | Chart components (risk distribution, peer comparison) |
| Lucide React | ≥0.577 | ISC | Icon set |
| react-force-graph-2d | ≥1.29 | MIT | Network graph visualization |
| clsx / tailwind-merge | ≥2.1 / ≥3.5 | MIT | Conditional class name utilities |

### Dev / CI Tools

| Tool | Purpose |
|---|---|
| Ruff | Python linter and formatter |
| mypy | Python static type checker |
| pytest + pytest-asyncio | Python test framework |
| bandit | Python SAST scanner |
| pip-audit | Python dependency CVE scanner |
| gitleaks | Secret scanning |
| CycloneDX | Software Bill of Materials (SBOM) generation |
