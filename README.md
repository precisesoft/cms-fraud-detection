# CMS Proactive Program Integrity

> Detecting anomalous provider behavior to prevent fraud, waste, and abuse before improper payments occur.

**Hackathon**: Government AI Hackathon — 14-day sprint
**Challenge**: Proactive Program Integrity (CMS)
**Status**: Incubating
**Current Phase**: Solutioning sprint active; final artifacts due March 25, 2026

## Start Here

- [Hackathon kickoff brief](docs/hackathon-kickoff.md)
- [Orientation meeting notes](docs/orientation-meeting-notes.md)
- [Team kickoff brief](docs/team-kickoff-brief.md)
- [Problem statement](docs/problem-statement.md)
- [Demo data research and graph strategy](docs/demo-data-research-plan.md)
- [Open questions for the project lead](docs/open-questions.md)
- [Official source register](docs/source-register.md)
- [Challenge research brief](docs/challenge-research.md)
- [Public dataset catalog](docs/dataset-catalog.md)

## Hackathon Envelope

- Team formation, use-case, and environment lock: March 6-March 11, 2026
- Solutioning sprint: March 12-March 25, 2026
- Submission lock: Wednesday, March 25, 2026 at 5:00 PM
- Technical evaluation: Thursday, March 26, 2026 based on orientation Q&A
- Demo day and judging: Friday, March 27, 2026 in Reston, Virginia
- Team rules: 2-5 members with at least one designated team lead
- Submission access: code may stay private if judges and the AI working group can review it
- Submission materials: must include enough for evaluation, such as a demo, README, or presentation
- AI tool usage is allowed but must be disclosed
- Public datasets only; no PHI
- Only original work created during the hackathon is eligible
- Open-source tools and libraries must be disclosed
- Explainability is required, not optional
- Cloud-native architecture is encouraged
- Final package must include submitted solution artifacts by March 25 plus a working demo,
  architecture diagram, risk-scoring explanation, responsible AI considerations, and a 5-minute
  "Path to CMS Pilot" briefing

## Planning Focus

This repository is the planning and incubation home for the CMS challenge. The immediate job is to
lock scope, datasets, judging narrative, and demo flow before committing to implementation.

The current repo state is documentation-first with empty Python package scaffolding. The architecture,
project tree, and commands below describe the intended build-out once implementation begins.

## Problem Statement

CMS loses an estimated $60B+ annually to improper payments across Medicare and Medicaid. Current detection is largely reactive — fraud is identified after payments are made. This project builds an AI system that proactively identifies anomalous provider billing patterns, flags high-risk claims before payment, and provides explainable risk scores that human reviewers can act on.

## Key Principles

1. **Explainable AI** — Every risk score has a human-readable explanation
2. **Transparent Scoring** — Full traceability from raw data to risk flag
3. **Scalable Architecture** — Cloud-native, handles national-scale claims volume
4. **Mission-Ready** — Clear pathway from MVP to agency pilot

## Architecture

> Full architecture specification: [docs/architecture-v3.md](docs/architecture-v3.md)

![System Architecture](docs/diagrams/01-system-architecture.png)

### Data Flow

![Data Pipeline](docs/diagrams/03-data-pipeline.png)

### Scoring Engine

![Scoring Engine](docs/diagrams/04-scoring-engine.png)

### Deployment

![Deployment Architecture](docs/diagrams/02-deployment-architecture.png)

### All Diagrams

| Diagram                                                                 | Description                          |
| ----------------------------------------------------------------------- | ------------------------------------ |
| [System Architecture](docs/diagrams/01-system-architecture.png)         | Full-stack component map             |
| [Deployment Architecture](docs/diagrams/02-deployment-architecture.png) | CI/CD → EKS pipeline                 |
| [Data Pipeline](docs/diagrams/03-data-pipeline.png)                     | 19GB ETL flow                        |
| [Scoring Engine](docs/diagrams/04-scoring-engine.png)                   | Dual scoring with signal provenance  |
| [Evidence Graph](docs/diagrams/05-evidence-graph.png)                   | Neo4j relationship model             |
| [AI Reasoning](docs/diagrams/06-ai-reasoning.png)                       | Text-to-SQL + narrative flow         |
| [Demo User Journey](docs/diagrams/07-demo-user-journey.png)             | 5-7 min demo script                  |
| [Signal Taxonomy](docs/diagrams/08-signal-taxonomy.png)                 | Risk + legitimacy signal definitions |
| [Fairness Evaluation](docs/diagrams/09-fairness-evaluation.png)         | Responsible AI metrics pipeline      |
| [Path to CMS Pilot](docs/diagrams/10-path-to-pilot.png)                 | MVP → Pilot → Production roadmap     |

## Public Data Sources

| Dataset                                 | Source       | Use                                             |
| --------------------------------------- | ------------ | ----------------------------------------------- |
| Medicare Provider Utilization & Payment | data.cms.gov | Billing patterns, service volumes, charges      |
| Medicare Part D Prescriber              | data.cms.gov | Prescription patterns, opioid flags             |
| LEIE Exclusion List                     | oig.hhs.gov  | Labeled fraud positives for supervised learning |
| Medicare Provider Compare               | data.cms.gov | Provider metadata, specialties, locations       |
| HCPCS/CPT Code Reference                | cms.gov      | Service code descriptions for explainability    |

## Tech Stack

| Layer         | Technology               | Why                                                    |
| ------------- | ------------------------ | ------------------------------------------------------ |
| Frontend      | Next.js 15 + TypeScript  | SSR, app router, API routes as BFF                     |
| UI Components | shadcn/ui + Tailwind CSS | Polished, accessible, fast to build                    |
| Charts        | Recharts                 | React-native, composable, AI can specify chart configs |
| Backend       | Python 3.12 + FastAPI    | Async, auto-docs, scoring engine                       |
| Database      | PostgreSQL 16            | Operational store, SQL queries, production-grade       |
| Graph         | Neo4j 5                  | Relationship traversal, Cypher queries                 |
| ETL           | DuckDB + Polars          | One-time data processing (not runtime)                 |
| AI            | AWS Bedrock (Claude)     | FedRAMP authorized, GovCloud-ready                     |
| Containers    | Docker + docker-compose  | Local dev, multi-service                               |
| CI            | GitHub Actions           | Lint, test, build, coverage                            |
| CD            | ArgoCD                   | GitOps deployment to EKS                               |
| Registry      | Amazon ECR               | AWS-native container image store                       |

## Quickstart

```bash
# Clone and configure
git clone git@github.com:precisesoft/cms-fraud-detection.git
cd cms-fraud-detection
cp .env.example .env  # Edit with your AWS credentials

# Start all services
docker compose up -d

# Run ETL pipeline (one-time)
docker compose exec backend python -m backend.src.etl.load

# Access the app
# Frontend: http://localhost:3000
# Backend API docs: http://localhost:8000/docs

# Run tests
docker compose exec backend pytest
```

## Team

- Arun Sanna — AI/ML Engineering, Architecture
