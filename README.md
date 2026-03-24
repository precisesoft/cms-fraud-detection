# Argus — CMS Proactive Program Integrity

> Detecting anomalous provider behavior to prevent fraud, waste, and abuse before improper payments occur.

**Hackathon**: Government AI Hackathon — 10-day sprint (Mar 14–24, 2026)
**Challenge**: Proactive Program Integrity (CMS)
**Live App**: [argus.precise-lab.com](https://argus.precise-lab.com)
**Submission Deadline**: March 25, 2026 at 5:00 PM ET

### By the Numbers

| Metric                    | Value                                                                         |
| ------------------------- | ----------------------------------------------------------------------------- |
| Revocation detection rate | **91%** from billing patterns alone                                           |
| Explainable signals       | 13 (6 risk + 7 legitimacy)                                                    |
| API endpoints             | 14                                                                            |
| Frontend pages            | 12 interactive views                                                          |
| Test coverage             | 99% backend, 98% frontend                                                     |
| Issues delivered          | 181 issues, 162 PRs, 179 commits                                              |
| CI/CD pipeline            | 8-stage unified (Gate → Security → Quality → Build → Scan → Release → Deploy) |
| Infrastructure            | AWS EKS + Istio + ArgoCD (GitOps)                                             |

## Documentation

- [Problem statement](docs/problem-statement.md)
- [Architecture (v3)](docs/architecture-v3.md)
- [Demo script](docs/demo-script.md)
- [Development process](docs/development-process.md)
- [AI/OSS disclosure](docs/ai-oss-disclosure.md)
- [Path to CMS pilot](docs/path-to-cms-pilot.md)
- [Risk scoring methodology](docs/risk-scoring-methodology.md)
- [Responsible AI considerations](docs/responsible-ai-considerations.md)
- [Model card — Isolation Forest](docs/model-card-isolation-forest.md)
- [User personas](docs/personas.md)

<details>
<summary>Pre-sprint research (historical)</summary>

- [Hackathon kickoff brief](docs/research/hackathon-kickoff.md)
- [Orientation meeting notes](docs/research/orientation-meeting-notes.md)
- [Team kickoff brief](docs/research/team-kickoff-brief.md)
- [Demo data research and graph strategy](docs/research/demo-data-research-plan.md)
- [Open questions](docs/research/open-questions.md)
- [Official source register](docs/research/source-register.md)
- [Challenge research brief](docs/research/challenge-research.md)
- [Public dataset catalog](docs/research/dataset-catalog.md)

</details>

## Hackathon Envelope

- Sprint: March 12–25, 2026 | Demo day: March 27, Reston, VA
- Public datasets only, no PHI | AI usage disclosed | Explainability required
- Deliverables: working demo, architecture diagrams, risk-scoring methodology, responsible AI considerations, 5-min "Path to CMS Pilot" briefing

## Sprint Timeline

| Phase                    | Due    | Status   | Key Deliverables                                       |
| ------------------------ | ------ | -------- | ------------------------------------------------------ |
| Phase 0: Project Spine   | Mar 14 | **Done** | Monorepo, CI/CD, Dockerfiles, branch protection        |
| Phase 1: Data Foundation | Mar 18 | **Done** | 19GB ETL, 13K cases + 10K providers, Neo4j graph       |
| Phase 2: Scoring + API   | Mar 20 | **Done** | Scoring engine, all REST endpoints, peer baselines     |
| Phase 3: AI Signals      | Mar 22 | **Done** | Text-to-SQL, risk narratives, anomaly detection        |
| Phase 4: User Interface  | Mar 24 | **Done** | Claims simulator, investigation workflow, chat sidebar |
| Phase 4b: Live Monitor   | Mar 24 | **Done** | SSE real-time payment monitor, ML explainability UI    |
| Phase 5: Ship            | Mar 25 | **Done** | Demo script, AI/OSS disclosure, judge access           |

**Demo Day**: March 27, 2026 — Reston, Virginia

## Problem Statement

CMS loses an estimated $60B+ annually to improper payments across Medicare and Medicaid. Current detection is largely reactive — fraud is identified after payments are made. This project builds a decision-support system that identifies anomalous provider billing patterns, surfaces evidence-backed risk cases, and provides explainable scores that human reviewers can act on in real time, proactively.

**Validated result:** In retrospective testing, our scoring system detected **91% of eventually-revoked providers from billing patterns alone** — before CMS acted on revocation.

## Judge Resources

**Live App**: [argus.precise-lab.com](https://argus.precise-lab.com) | **Validation Endpoint**: [/api/validation](https://argus.precise-lab.com/api/validation)

| Deliverable                     | Document                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------ |
| Risk Scoring Methodology        | [docs/risk-scoring-methodology.md](docs/risk-scoring-methodology.md)           |
| Responsible AI Considerations   | [docs/responsible-ai-considerations.md](docs/responsible-ai-considerations.md) |
| AI & Open Source Disclosure     | [docs/ai-oss-disclosure.md](docs/ai-oss-disclosure.md)                         |
| Path to CMS Pilot (5-min brief) | [docs/path-to-cms-pilot.md](docs/path-to-cms-pilot.md)                         |
| Demo Script (5-7 min)           | [docs/demo-script.md](docs/demo-script.md)                                     |
| Isolation Forest Model Card     | [docs/model-card-isolation-forest.md](docs/model-card-isolation-forest.md)     |
| Development Process             | [docs/development-process.md](docs/development-process.md)                     |
| Architecture Diagrams           | [docs/diagrams/](docs/diagrams/)                                               |

## Key Principles

1. **Explainable Scoring** — Every risk score traces to specific signals with data provenance
2. **Transparent Decision Logic** — Rule-based scoring with peer comparison, validated against revocation outcomes
3. **AI-Assisted Investigation** — LLM-powered natural language queries, risk narratives, and chat interface for analysts
4. **Cloud-Native Architecture** — EKS, ArgoCD, Terraform — designed for scale
5. **Real-Time Scoring** — SSE-streamed live payment monitor scores claims in under 50ms
6. **Mission-Ready** — Clear pathway from MVP to agency pilot

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

| Layer    | Technology                                                                        | Status |
| -------- | --------------------------------------------------------------------------------- | ------ |
| Frontend | Vite + React 19 + TypeScript + Tailwind v4 + Recharts                             | Live   |
| Backend  | Python 3.12 + FastAPI + psycopg                                                   | Live   |
| Database | PostgreSQL 16 (EKS StatefulSet)                                                   | Live   |
| Graph    | Neo4j 5 Community (EKS StatefulSet)                                               | Live   |
| Scoring  | Rule-based taxonomy (13 signals) + Isolation Forest + per-provider explainability | Live   |
| AI       | AWS Bedrock (Claude) — narratives, text-to-SQL, chat                              | Live   |
| ETL      | DuckDB + Polars                                                                   | Done   |
| CI/CD    | GitHub Actions (unified pipeline) + ECR + ArgoCD                                  | Live   |
| Infra    | AWS EKS + Istio + Terraform                                                       | Live   |

## Quickstart

```bash
# Clone
git clone git@github.com:precisesoft/cms-fraud-detection.git
cd cms-fraud-detection

# Start all services (Postgres, Neo4j, API, Frontend)
docker compose up -d

# --- Backend ---
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest --cov=src -q                    # Run backend tests
uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000

# --- Frontend ---
cd frontend
npm install
npm run dev                            # http://localhost:3000
npm test                               # Run frontend tests

# API docs: http://localhost:8000/docs
```

## Team

- Arun Sanna — Lead, AI/ML Engineering, Architecture
- Bibek Poudel — Backend, Infrastructure
