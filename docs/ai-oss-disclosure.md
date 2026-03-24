# AI & Open-Source Disclosure

> Required hackathon disclosure per competition rules.

## AI Tools Used

| Tool                    | Provider                  | Purpose                                                                     |
| ----------------------- | ------------------------- | --------------------------------------------------------------------------- |
| Claude (Sonnet / Haiku) | Anthropic via AWS Bedrock | Risk narrative generation, text-to-SQL query translation, AI chat interface |
| GitHub Copilot          | GitHub / OpenAI           | Developer productivity — code completion and suggestions during development |
| Claude (API)            | Anthropic                 | Architecture review, documentation drafting, code review assistance         |

All AI-generated code and content was reviewed, tested, and validated by the development team before inclusion. No AI output was accepted without human review.

## Open-Source Libraries

### Backend (Python)

| Library      | Version | License      | Purpose                             |
| ------------ | ------- | ------------ | ----------------------------------- |
| FastAPI      | 0.115.x | MIT          | REST API framework                  |
| psycopg      | 3.x     | LGPL-3.0     | PostgreSQL async driver             |
| Pydantic     | 2.x     | MIT          | Data validation and serialization   |
| Polars       | 1.x     | MIT          | Dataframe processing (ETL pipeline) |
| DuckDB       | 0.x     | MIT          | In-process analytics (ETL)          |
| uvicorn      | 0.x     | BSD          | ASGI server                         |
| scikit-learn | 1.x     | BSD-3-Clause | Isolation Forest anomaly detection  |
| boto3        | 1.x     | Apache-2.0   | AWS Bedrock SDK                     |
| pytest       | 8.x     | MIT          | Test framework                      |
| ruff         | 0.x     | MIT          | Linting and formatting              |
| mypy         | 1.x     | MIT          | Static type checking                |

### Frontend (Vite + React)

| Library           | Version | License    | Purpose                      |
| ----------------- | ------- | ---------- | ---------------------------- |
| React             | 19.x    | MIT        | UI component library         |
| React Router      | 7.x     | MIT        | Client-side routing (SPA)    |
| Vite              | 6.x     | MIT        | Build tool and dev server    |
| Tailwind CSS      | 4.x     | MIT        | Utility-first CSS framework  |
| Recharts          | 3.x     | MIT        | Data visualization / charts  |
| react-simple-maps | 3.x     | MIT        | US choropleth risk heatmap   |
| Lucide React      | 0.5x    | ISC        | Icon library                 |
| Motion            | 12.x    | MIT        | Animation library            |
| TypeScript        | 5.x     | Apache-2.0 | Static typing for JavaScript |
| Vitest            | 4.x     | MIT        | Unit test framework          |
| MSW               | 2.x     | MIT        | API mocking for tests        |

### Infrastructure

| Tool              | License            | Purpose                      |
| ----------------- | ------------------ | ---------------------------- |
| PostgreSQL 16     | PostgreSQL License | Relational database          |
| Neo4j 5 Community | GPL-3.0            | Graph database               |
| Docker            | Apache-2.0         | Containerization             |
| Kubernetes (EKS)  | Apache-2.0         | Container orchestration      |
| Terraform         | BSL-1.1            | Infrastructure as code       |
| ArgoCD            | Apache-2.0         | GitOps continuous deployment |
| GitHub Actions    | GitHub ToS         | CI/CD pipelines              |

## Data Sources

All data used in this project is publicly available. No Protected Health Information (PHI) was used or accessed at any point.

| Dataset                                                            | Source           | License                         |
| ------------------------------------------------------------------ | ---------------- | ------------------------------- |
| Medicare Physician & Other Practitioners — by Provider and Service | CMS data.cms.gov | Public Domain (U.S. Government) |
| Medicare Fee-for-Service Public Provider Enrollment                | CMS data.cms.gov | Public Domain (U.S. Government) |
| CMS Provider Revocation File                                       | CMS data.cms.gov | Public Domain (U.S. Government) |

## Compliance

- All AI tool usage is disclosed per hackathon rules
- No proprietary or confidential data was shared with AI tools
- All open-source licenses are compatible with this project's use case
- No PHI, PII, or sensitive government data was used
