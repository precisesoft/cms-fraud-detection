# CMS Proactive Program Integrity

> Detecting anomalous provider behavior to prevent fraud, waste, and abuse before improper payments occur.

**Hackathon**: Government AI Hackathon — 14-day sprint
**Challenge**: Proactive Program Integrity (CMS)
**Live App**: [argus.precise-lab.com](https://argus.precise-lab.com)
**Submission Deadline**: March 25, 2026 at 5:00 PM ET

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

## Sprint Timeline

| Phase                    | Due    | Status          | Key Deliverables                                       |
| ------------------------ | ------ | --------------- | ------------------------------------------------------ |
| Phase 0: Project Spine   | Mar 14 | **Done**        | Monorepo, CI/CD, Dockerfiles, branch protection        |
| Phase 1: Data Foundation | Mar 18 | **Done**        | 19GB ETL, 13K cases + 10K providers, Neo4j graph       |
| Phase 2: Scoring + API   | Mar 20 | **Done**        | Scoring engine, all REST endpoints, peer baselines     |
| Phase 3: AI Intelligence | Mar 22 | **In Progress** | Text-to-SQL, risk narratives, chat with charts         |
| Phase 4: User Interface  | Mar 24 | **In Progress** | Claims simulator, investigation workflow, chat sidebar |
| Phase 5: Ship            | Mar 26 | Pending         | Demo script, AI/OSS disclosure, judge access           |

**Demo Day**: March 27, 2026 — Reston, Virginia

## Problem Statement

CMS loses an estimated $60B+ annually to improper payments across Medicare and Medicaid. Current detection is largely reactive — fraud is identified after payments are made. This project builds a decision-support system that identifies anomalous provider billing patterns, surfaces evidence-backed risk cases, and provides explainable scores that human reviewers can act on.

**Validated result:** In retrospective testing, our scoring system detected **91% of eventually-revoked providers from billing patterns alone** — before CMS acted on revocation.

## Judge Resources

**Live App**: [argus.precise-lab.com](https://argus.precise-lab.com) | **Validation Endpoint**: [/api/validation](/api/validation)

| Deliverable                     | Document                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------ |
| Risk Scoring Methodology        | [docs/risk-scoring-methodology.md](docs/risk-scoring-methodology.md)           |
| Responsible AI Considerations   | [docs/responsible-ai-considerations.md](docs/responsible-ai-considerations.md) |
| AI & Open Source Disclosure     | [docs/ai-oss-disclosure.md](docs/ai-oss-disclosure.md)                         |
| Path to CMS Pilot (5-min brief) | [docs/path-to-cms-pilot.md](docs/path-to-cms-pilot.md)                         |
| Demo Script (5-7 min)           | [docs/demo-script.md](docs/demo-script.md)                                     |
| Isolation Forest Model Card     | [docs/model-card-isolation-forest.md](docs/model-card-isolation-forest.md)     |
| Architecture Diagrams           | [docs/diagrams/](docs/diagrams/)                                               |

## Key Principles

1. **Explainable Scoring** — Every risk score traces to specific signals with data provenance
2. **Transparent Decision Logic** — Rule-based scoring with peer comparison, validated against revocation outcomes
3. **AI-Assisted Investigation** — LLM-powered natural language queries, risk narratives, and chat interface for analysts
4. **Cloud-Native Architecture** — EKS, ArgoCD, Terraform — designed for scale
5. **Mission-Ready** — Clear pathway from MVP to agency pilot

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

All datasets are publicly available and currently downloadable. No PHI is used.

### Active (used in scoring pipeline)

| Dataset                                                                                                                                                                                                                              | Source       | Use                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ | --------------------------------------------------------------- |
| [Medicare Physician & Other Practitioners — by Provider and Service](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service) | data.cms.gov | Core billing patterns, service volumes, charges, peer baselines |
| [Medicare Physician & Other Practitioners — by Provider](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners)                                                                            | data.cms.gov | Provider-level totals (benes, services, payments)               |
| [Public Provider Enrollment](https://data.cms.gov/provider-data/dataset/mj5m-pzi6)                                                                                                                                                   | data.cms.gov | Enrollment status verification                                  |
| Revoked Providers (Q1 2026)                                                                                                                                                                                                          | data.cms.gov | Revocation flag for risk scoring                                |

### Reference only (not used in current pipeline)

| Dataset                                                                                                                                                              | Source       | Notes                                        |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | -------------------------------------------- |
| [OIG LEIE Exclusion List](https://oig.hhs.gov/exclusions/)                                                                                                           | oig.hhs.gov  | Potential enrichment; weak NPI join coverage |
| [Medicare Part D Prescribers](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug) | data.cms.gov | Potential prescribing-pattern enrichment     |

## Tech Stack

| Layer    | Technology                                           | Status |
| -------- | ---------------------------------------------------- | ------ |
| Frontend | Next.js 16.2.0 + TypeScript + Tailwind + shadcn/ui   | Live   |
| Backend  | Python 3.12 + FastAPI + psycopg                      | Live   |
| Database | PostgreSQL 16 (EKS StatefulSet)                      | Live   |
| Graph    | Neo4j 5 Community (EKS StatefulSet)                  | Live   |
| Scoring  | Rule-based taxonomy (14 signals) + anomaly detection | Live   |
| AI       | AWS Bedrock (Claude) — narratives, text-to-SQL, chat | Live   |
| ETL      | DuckDB + Polars                                      | Done   |
| CI/CD    | GitHub Actions + ECR + ArgoCD                        | Live   |
| Infra    | AWS EKS + Istio + Terraform                          | Live   |

## Quickstart

```bash
# Clone
git clone git@github.com:precisesoft/cms-fraud-detection.git
cd cms-fraud-detection

# Start Postgres
docker compose up -d

# Install Python dependencies
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest --cov=src -q

# Start API server (requires Postgres running)
uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000
# API docs: http://localhost:8000/docs
```

## Team

- Arun Sanna — AI/ML Engineering, Architecture
