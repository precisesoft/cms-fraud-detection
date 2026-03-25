# Argus — CMS Proactive Program Integrity

> **91% of eventually-revoked providers detected from billing patterns alone** — before CMS acted on revocation.

CMS loses an estimated **$60 billion annually** to improper payments across Medicare and Medicaid. Current detection is largely reactive — fraud is identified after payments are made, forcing a costly "pay-and-chase" cycle. Argus is a decision-support system that identifies anomalous provider billing patterns, surfaces evidence-backed risk cases, and provides explainable scores that human reviewers can act on **proactively, in real time**.

**Live App**: [argus.precise-lab.com](https://argus.precise-lab.com) | **GitHub**: [precisesoft/cms-fraud-detection](https://github.com/precisesoft/cms-fraud-detection) | **CI/CD Pipeline**: [Actions](https://github.com/precisesoft/cms-fraud-detection/actions) | **Issues & PRs**: [181 issues](https://github.com/precisesoft/cms-fraud-detection/issues?q=is%3Aissue) / [162 PRs](https://github.com/precisesoft/cms-fraud-detection/pulls?q=is%3Apr)
**Demo Script**: [docs/demo-script.md](docs/demo-script.md) | **Hackathon**: Government AI Hackathon (Mar 14–25, 2026)

![Dashboard](screenshots/01-dashboard.png)

---

## How It Works

```
  19GB real CMS data          13 explainable signals           Evidence-backed cases
 (4 public datasets)    ──>  (risk + legitimacy scoring)  ──>  for human investigators
                              + ML anomaly detection            + AI-generated narratives
```

1. **Ingest** — 19GB of real, public Medicare data: 9.66M service lines across 10,282 providers from [data.cms.gov](https://data.cms.gov). No PHI. No synthetic data.
2. **Score** — Every provider-service case receives two independent scores: a **risk score** (how anomalous vs. peers) and a **legitimacy score** (how many trust indicators exist). 13 named signals, each with a threshold, weight, and data-source citation. Plus an independent Isolation Forest anomaly score with per-provider feature importance.
3. **Investigate** — Analysts review flagged cases with full signal breakdowns, peer comparison charts, evidence graphs, and AI-generated narratives. The system explains; the human decides.

---

## Validated Results

We didn't just build a scoring system — we validated it. We took all 335 revoked providers in our dataset, **removed the revocation flag**, and re-scored them using only behavioral signals.

| Metric                                    | Result    |
| ----------------------------------------- | --------- |
| Overall detection rate (revocation-blind) | **91.3%** |
| Billing abuse cases                       | **94%**   |
| Felony-related revocations                | **100%**  |
| Non-revoked provider baseline flagging    | 51.4%     |

**Methodology**: The retrospective validation endpoint (`/api/validation`) removes the `revoked_provider` signal (worth 25 points) and re-scores all providers using only peer z-scores, enrollment status, and billing patterns. This proves the behavioral signals alone have real discriminative power — the system doesn't just flag providers because they're already revoked.

**Try it live**: [argus.precise-lab.com/api/validation](https://argus.precise-lab.com/api/validation)

---

## What Makes This Different

### Dual Scoring — Risk AND Legitimacy

Traditional fraud detection produces a single risk score. Argus computes **two independent scores** for every case. A provider with high volume (risk signal) who is enrolled, Medicare-participating, and peer-aligned on all other metrics (legitimacy signals) won't be flagged — the legitimacy score contextualizes the risk. This reduces false positives and ensures providers aren't flagged on a single anomalous metric.

### Per-Provider ML Explainability

The Isolation Forest anomaly model provides per-provider feature importance via leave-one-out approximation — not a global average, but which specific features drive _this_ provider's anomaly score. Risk-increasing features shown in red, protective features in green, all computed in under 100ms.

### Real-Time Scoring

Claims stream via Server-Sent Events, scored by the 13-signal engine in **under 50 milliseconds**. No batch jobs, no overnight processing — proactive detection as payments arrive.

### Built-In Fairness Monitoring

A dedicated `/api/fairness` endpoint computes flagging rate disparities across geography and specialty using statistical parity difference, disparate impact ratio (EEOC four-fifths rule), and outlier detection. Configurable threshold. No demographic variables are used in scoring.

### AI-Assisted Investigation

AWS Bedrock Claude powers three capabilities: **text-to-SQL** (analysts ask questions in plain English), **risk narratives** (structured signals summarized in plain language), and **chat** (conversational investigation). All AI output is advisory — the scoring engine is fully deterministic and AI-free.

---

## The Product

### Dashboard — Aggregate Risk Overview

![Dashboard](screenshots/dashboard-live.png)

Total providers scored, risk distribution breakdown, geographic heatmap of state-level flagging patterns, and top-risk cases.

### Live Payment Monitor — Real-Time Scoring

![Live Monitor](screenshots/02-live-monitor-running.png)

Claims stream across a US map with pulsing risk dots. Each claim scored in <50ms. Click a flagged claim to investigate.

### Provider Detail — Signal Breakdown

![Provider Detail](screenshots/05-provider-detail-loaded.png)

Full signal decomposition: which signals fired, how many points each contributed, peer baseline comparisons, evidence graph, ML anomaly score with per-provider feature importance.

### Claims Simulator — Pre-Payment Screening

![Simulate](screenshots/03-simulate.png)

Submit a hypothetical claim and watch the scoring engine extract signals, compute risk + legitimacy, and generate an AI narrative — simulating what pre-payment screening would look like.

### Fairness Dashboard — Bias Monitoring

![Fairness](screenshots/08-fairness.png)

Statistical parity and disparate impact metrics across states and specialties. Outlier detection flags systemic bias.

### Investigation Workflow — Case Management

![Investigations](screenshots/11-investigations.png)

Triaged case queue with approve/flag/deny/escalate actions, audit trail, and AI chat sidebar for natural-language data queries.

---

## Government Readiness

Argus is designed to deploy into a government environment with minimal rework.

| Capability                       | Status                                                                                                                                                                                                           |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **FedRAMP Authorization**        | AWS Bedrock is FedRAMP High authorized. GovCloud deployment path documented.                                                                                                                                     |
| **Audit Trail**                  | Immutable `audit_log` captures every analyst action (approve, flag, deny, escalate) and every AI-generated SQL query with analyst ID, timestamp, and source IP.                                                  |
| **RBAC**                         | JWT-backed role-based access control is live.                                                                                                                                                                    |
| **Security Pipeline**            | 6 security tools run on every PR: gitleaks (secrets), bandit (SAST), pip-audit (Python CVEs), npm audit (JS CVEs), CycloneDX SBOMs, Trivy container scanning.                                                    |
| **SBOMs**                        | CycloneDX Software Bill of Materials generated for both backend and frontend on every build.                                                                                                                     |
| **No PHI Required**              | Works on public CMS data today. Connecting internal claims feeds is a data source change, not an architecture change.                                                                                            |
| **Integration with CMS Systems** | Designed to complement FPS (Fraud Prevention System), not replace it. FPS-flagged NPIs become investigation triggers in Argus. Evidence packages can feed into UCM (Unified Case Management) for UPIC workflows. |
| **Infrastructure as Code**       | Terraform-managed AWS resources with S3 state + DynamoDB locking. GitOps deployment via ArgoCD.                                                                                                                  |

**The path from hackathon to CMS pilot is a data connection change, not a rebuild.** Full briefing: [Path to CMS Pilot](docs/path-to-cms-pilot.md)

---

## Engineering Rigor

### 10-Day Sprint, Production-Grade Delivery

This was built in a 10-day hackathon sprint (Mar 14–24, 2026) using an AI-assisted agile process with two AI agents and a human orchestrator.

| Metric                   | Value                                                           |
| ------------------------ | --------------------------------------------------------------- |
| Issues tracked           | 181                                                             |
| Pull requests merged     | 162                                                             |
| Commits to main          | 179                                                             |
| Epics completed          | 19                                                              |
| Test coverage (backend)  | 99%                                                             |
| Test coverage (frontend) | 98%                                                             |
| CI/CD pipeline stages    | 8 (Gate → Security → Quality → Build → Scan → Release → Deploy) |
| Daily scoreboards        | 9 published                                                     |
| API endpoints            | 14 live                                                         |
| Frontend pages           | 12 interactive views                                            |

### Project Management Metrics

The sprint was managed with full agile discipline — not "hackathon chaos."

| Metric                     | Value                                                |
| -------------------------- | ---------------------------------------------------- |
| Story points delivered     | **480 SP** across 128 pointed issues                 |
| Sprint velocity            | Day 1: 0% → Day 5: 80% → Day 7: 91% → Day 8: 97%     |
| Backlog created Day 1      | 70 issues across 9 epics before any code was written |
| Issues added mid-sprint    | 111 (scope grew 2.6x as complexity was discovered)   |
| Avg PRs merged per day     | **16.2 PRs/day** over the sprint                     |
| Avg issues closed per day  | **18.1 issues/day** over the sprint                  |
| One issue = one PR         | Strict rule, zero exceptions. Clean git history.     |
| Copilot agent contribution | 43 PRs (27%), ~50 SP, ~3,500+ lines                  |
| Human contribution         | ~119 PRs (73%), ~430 SP, ~35,000+ lines              |

**Sprint velocity by phase:**

| Phase                        | Story Points | Issues  |
| ---------------------------- | ------------ | ------- |
| Phase 0: Spine / CI/CD       | 27 SP        | 13      |
| Phase 1: Data Foundation     | 50 SP        | 12      |
| Phase 2: Scoring + API       | 74 SP        | 18      |
| Phase 3: AI Reasoning        | 85 SP        | 16      |
| Phase 4: Frontend UI         | 138 SP       | 33      |
| Phase 5: Ship / Infra / Docs | 96 SP        | 34      |
| **Total**                    | **480 SP**   | **128** |

Daily scoreboards published in `docs/agile/` tracked issues opened vs. closed, PRs merged, CI pass rate, blockers, and decisions — every day for 9 consecutive days.

### Frameworks & Methodologies

This project applies recognized software engineering frameworks — not ad hoc hackathon shortcuts.

| Framework                              | Where Applied                                                                                                                                                                            |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agile Scrum**                        | Epic-driven sprint planning, daily scoreboards, velocity tracking, backlog grooming                                                                                                      |
| **Fibonacci Story Points**             | 1/2/3/5/8/13 scale based on PR diff size, files touched, complexity, integration points                                                                                                  |
| **Conventional Commits**               | Every commit follows `type(scope): description (#N)` — enforced by CI gate                                                                                                               |
| **BASSPC Self-Review**                 | Karpathy-inspired review methodology (Bloat, Assumptions, Scope, Sycophancy, Post-cleanup, CLI/IO) applied to every PR before merge                                                      |
| **GitOps**                             | ArgoCD watches `precise-manifests` repo as single source of truth for Kubernetes state                                                                                                   |
| **Infrastructure as Code**             | Terraform with S3 state backend + DynamoDB locking. Plan on PR, apply on merge                                                                                                           |
| **Mitchell et al. Model Card**         | Isolation Forest model documented per the [2019 model card framework](https://arxiv.org/abs/1810.03993)                                                                                  |
| **EEOC Four-Fifths Rule**              | Disparate impact ratio in fairness monitoring maps to the 80% threshold used in employment discrimination analysis                                                                       |
| **OWASP Top 10**                       | Security scanning (bandit SAST, gitleaks, pip-audit, npm audit) aligned with OWASP vulnerability categories                                                                              |
| **CycloneDX SBOM**                     | Software Bill of Materials generated for both backend and frontend on every build — supply chain transparency                                                                            |
| **SDLC with Branch Protection**        | Full CONTRIBUTING.md: branch → PR → CI green → review → squash merge → cleanup. No direct pushes to main.                                                                                |
| **Dual-Label Issue Taxonomy**          | Phase labels (`phase:0-spine` through `phase:5-ship`) + track labels (`backend`, `frontend`, `data`, `ai`, `infra`, `docs`) + priority labels (`P0-critical`, `P1-important`, `P2-nice`) |
| **Human-AI Collaborative Development** | Claude Code as agile orchestrator + GitHub Copilot SWE Agent as autonomous implementer + 10 specialized agent personas for role-based work                                               |

### AI-Assisted Development Process

Two AI agents collaborated under human orchestration:

- **Claude Code** (orchestrator): Broke epics into issues, assigned work, reviewed every PR using BASSPC methodology, merged, and ran post-merge cleanup. Managed the full agile lifecycle.
- **GitHub Copilot SWE Agent**: Picked up assigned issues, wrote code on branches, opened draft PRs. **43 PRs authored** (27% of all PRs). Cannot self-approve — all merges were human-reviewed.

Strict discipline: one issue per PR, conventional commits, CI must pass before merge. Full process: [Development Process](docs/development-process.md)

### 10 Copilot Agent Personas ([`.github/agents/`](.github/agents/))

Each agent is a detailed instruction file that shapes the Copilot SWE Agent's behavior based on the type of work assigned. Every persona includes project context, architecture awareness, coding standards, testing requirements, and explicit "what NOT to do" constraints.

| Agent                  | File                                                                    | Role                                                   | Key Capabilities                                                                                   |
| ---------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| **Senior Developer**   | [`senior-developer.agent.md`](.github/agents/senior-developer.agent.md) | End-to-end feature implementation                      | Full backend + frontend architecture awareness, 11 API endpoints reference, testing standards      |
| **AI Engineer**        | [`ai-engineer.agent.md`](.github/agents/ai-engineer.agent.md)           | LLM prompts, text-to-SQL, Bedrock integration          | 7 SQL guardrails, prompt engineering guidelines, model configuration, adversarial testing          |
| **Data Scientist**     | [`data-scientist.agent.md`](.github/agents/data-scientist.agent.md)     | ML models, feature engineering, statistical validation | Isolation Forest, 63-column feature table, retrospective validation, polars-only data manipulation |
| **Frontend Developer** | [`frontend-dev.agent.md`](.github/agents/frontend-dev.agent.md)         | Vite + React 19 SPA pages and components               | Full design system (colors, typography, spacing), 18 API integration points, component patterns    |
| **Test Engineer**      | [`test-engineer.agent.md`](.github/agents/test-engineer.agent.md)       | Test coverage, edge cases, async endpoint tests        | pytest + pytest-asyncio, mock patterns, coverage thresholds                                        |
| **Bug Fixer**          | [`bug-fixer.agent.md`](.github/agents/bug-fixer.agent.md)               | Minimal targeted fixes with regression tests           | Root cause analysis, smallest possible diff, regression prevention                                 |
| **Security Auditor**   | [`security-auditor.agent.md`](.github/agents/security-auditor.agent.md) | OWASP checks, bandit/pip-audit findings                | SQL injection prevention, input validation, secret scanning                                        |
| **Code Reviewer**      | [`code-reviewer.agent.md`](.github/agents/code-reviewer.agent.md)       | BASSPC review methodology on PRs                       | Bloat, Assumptions, Scope, Sycophancy, Post-cleanup, CLI/IO checks                                 |
| **Docs Writer**        | [`docs-writer.agent.md`](.github/agents/docs-writer.agent.md)           | README, architecture docs, API docs                    | Technical writing standards, diagram references, judge deliverables                                |
| **Technical PM**       | [`technical-pm.agent.md`](.github/agents/technical-pm.agent.md)         | Issue triage, epic breakdown, acceptance criteria      | Sprint planning, priority labels, story point estimation                                           |

Each persona enforces project conventions: conventional commits, branch naming (`<type>/<N>-<desc>`), `Closes #N` in PR bodies, and full local CI verification before push.

### CI/CD Pipeline

Single unified workflow. Every PR runs through:

```
Gate (PR title) → Security (4 scanners) → Quality Backend (ruff + mypy + pytest 95%) → Quality Frontend (eslint + tsc + vitest 80%) → Build (Docker + SBOMs) → Scan (Trivy)
```

On merge: Release (ECR push with SHA tags) → Deploy (GitOps via ArgoCD to EKS).

### GitOps Deployment

```
Push to main → Build images → Push to ECR → Update SHA tags in precise-manifests repo → ArgoCD auto-syncs to EKS
```

Two-repo separation: application code in `cms-fraud-detection`, Kubernetes manifests in `precise-manifests`. ArgoCD is the sole deployer.

---

## Architecture

> Full specification: [Architecture (v3)](docs/architecture-v3.md)

![System Architecture](docs/diagrams/01-system-architecture.png)

### Tech Stack

| Layer    | Technology                                                | Purpose                                      |
| -------- | --------------------------------------------------------- | -------------------------------------------- |
| Frontend | Vite + React 19 + TypeScript + Tailwind v4 + Recharts     | 12-page SPA with responsive design           |
| Backend  | Python 3.12 + FastAPI + psycopg (async)                   | 14 REST endpoints, auto-documented           |
| Database | PostgreSQL 16 (EKS StatefulSet, 20Gi gp3)                 | Relational queries, provider/case data       |
| Graph    | Neo4j 5 Community (EKS StatefulSet, 10Gi gp3)             | Evidence relationships, network analysis     |
| Scoring  | Deterministic rule engine (13 signals) + Isolation Forest | Auditable, reproducible, peer comparison     |
| AI       | AWS Bedrock (Claude Sonnet 4.6 + Haiku 4.5)               | Narratives, text-to-SQL, chat — FedRAMP High |
| ETL      | DuckDB + Polars                                           | 19GB data pipeline                           |
| CI/CD    | GitHub Actions → ECR → ArgoCD                             | 8-stage unified pipeline with GitOps         |
| Infra    | AWS EKS + Istio + Terraform                               | Container-native, horizontally scalable      |

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

---

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

---

## Documentation

### Judge Deliverables

| Deliverable                     | Document                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------ |
| Risk Scoring Methodology        | [docs/risk-scoring-methodology.md](docs/risk-scoring-methodology.md)           |
| Responsible AI Considerations   | [docs/responsible-ai-considerations.md](docs/responsible-ai-considerations.md) |
| AI & Open Source Disclosure     | [docs/ai-oss-disclosure.md](docs/ai-oss-disclosure.md)                         |
| Path to CMS Pilot (5-min brief) | [docs/path-to-cms-pilot.md](docs/path-to-cms-pilot.md)                         |
| Demo Script (5-7 min)           | [docs/demo-script.md](docs/demo-script.md)                                     |
| Isolation Forest Model Card     | [docs/model-card-isolation-forest.md](docs/model-card-isolation-forest.md)     |
| Development Process             | [docs/development-process.md](docs/development-process.md)                     |
| Architecture (v3)               | [docs/architecture-v3.md](docs/architecture-v3.md)                             |
| Architecture Diagrams           | [docs/diagrams/](docs/diagrams/)                                               |
| User Personas                   | [docs/personas.md](docs/personas.md)                                           |

### Additional Documentation

- [Problem statement](docs/problem-statement.md)

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

---

## Quickstart

```bash
# Clone
git clone https://github.com/arunsanna/cms-fraud-detection.git
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

---

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

---

## Team

- **Arun Sanna** — Lead, AI/ML Engineering, Architecture
- **Bibek Poudel** — Backend, Infrastructure
