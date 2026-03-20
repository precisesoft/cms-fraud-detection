# AI & Open-Source Disclosure

> Required hackathon disclosure per competition rules.

## AI Tools Used

| Tool | Provider | Purpose |
|---|---|---|
| Claude (Sonnet / Haiku) | Anthropic via AWS Bedrock | Risk narrative generation, text-to-SQL query translation, AI chat interface |
| GitHub Copilot | GitHub / OpenAI | Developer productivity — code completion and suggestions during development |
| Claude (API) | Anthropic | Architecture review, documentation drafting, code review assistance |

All AI-generated code and content was reviewed, tested, and validated by the development team before inclusion. No AI output was accepted without human review.

## Open-Source Libraries

### Backend (Python)

| Library | Version | License | Purpose |
|---|---|---|---|
| FastAPI | 0.115.x | MIT | REST API framework |
| psycopg | 3.x | LGPL-3.0 | PostgreSQL async driver |
| Pydantic | 2.x | MIT | Data validation and serialization |
| Polars | 0.x | MIT | Dataframe processing (ETL pipeline) |
| DuckDB | 0.x | MIT | In-process analytics (ETL) |
| uvicorn | 0.x | BSD | ASGI server |
| scikit-learn | 1.x | BSD-3-Clause | Isolation Forest anomaly detection |
| boto3 | 1.x | Apache-2.0 | AWS Bedrock SDK |
| pytest | 7.x | MIT | Test framework |
| ruff | 0.x | MIT | Linting and formatting |
| mypy | 1.x | MIT | Static type checking |

### Frontend (Node.js / Next.js)

| Library | Version | License | Purpose |
|---|---|---|---|
| Next.js | 16.2.0 | MIT | React framework (App Router) |
| React | 19.x | MIT | UI component library |
| Tailwind CSS | 4.x | MIT | Utility-first CSS framework |
| shadcn/ui | latest | MIT | Accessible component library |
| Recharts | 2.x | MIT | Data visualization / charts |
| TypeScript | 5.x | Apache-2.0 | Static typing for JavaScript |

### Infrastructure

| Tool | License | Purpose |
|---|---|---|
| PostgreSQL 16 | PostgreSQL License | Relational database |
| Neo4j 5 Community | GPL-3.0 | Graph database |
| Docker | Apache-2.0 | Containerization |
| Kubernetes (k3s) | Apache-2.0 | Container orchestration |
| Terraform | BSL-1.1 | Infrastructure as code |
| ArgoCD | Apache-2.0 | GitOps continuous deployment |
| GitHub Actions | GitHub ToS | CI/CD pipelines |

## Data Sources

All data used in this project is publicly available. No Protected Health Information (PHI) was used or accessed at any point.

| Dataset | Source | License |
|---|---|---|
| Medicare Physician & Other Practitioners — by Provider and Service | CMS data.cms.gov | Public Domain (U.S. Government) |
| Medicare Fee-for-Service Public Provider Enrollment | CMS data.cms.gov | Public Domain (U.S. Government) |
| CMS Provider Revocation File | CMS data.cms.gov | Public Domain (U.S. Government) |

## Compliance

- All AI tool usage is disclosed per hackathon rules
- No proprietary or confidential data was shared with AI tools
- All open-source licenses are compatible with this project's use case
- No PHI, PII, or sensitive government data was used
