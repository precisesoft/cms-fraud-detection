# Development Process

> How Argus was built: AI-assisted agile development with automated CI/CD delivery.

## By the Numbers

| Metric                      | Value                           |
| --------------------------- | ------------------------------- |
| Sprint duration             | 10 days (Mar 14 – Mar 24, 2026) |
| Total issues tracked        | 181                             |
| Total pull requests         | 162                             |
| Commits to main             | 179                             |
| Epics completed             | 19                              |
| Daily scoreboards published | 9                               |
| Test coverage (backend)     | 99%                             |
| Test coverage (frontend)    | 98%                             |

## AI-Assisted Development

This project was built using a human-AI collaborative workflow with two AI agents:

### GitHub Copilot SWE Agent

[`copilot-swe-agent`](https://docs.github.com/en/copilot/using-github-copilot/using-copilot-coding-agent) is a GitHub-native coding agent that picks up assigned issues, writes code on a branch, and opens draft PRs.

- **43 PRs authored** by Copilot (27% of all PRs)
- Configured via `.github/copilot-setup-steps.yml` (installs deps, runs linters)
- Guided by `.github/copilot-instructions.md` (project conventions, stack, code style)
- Has **write access** to the repo so CI runs without manual approval
- Cannot self-approve or merge — always opens draft PRs for human review

### Claude Code (Orchestrator)

Claude Code served as the human-side orchestrator, operating the agile workflow:

1. **Plan** — Break epics into issues with acceptance criteria
2. **Assign** — Label issue `in-progress`, assign to `copilot-swe-agent`
3. **Monitor** — Check for PR creation, review diffs, watch CI status
4. **Review** — BASSPC self-review methodology on every PR
5. **Merge** — Squash merge when CI is green
6. **Cleanup** — Verify issue closed, comment PR#, update epic checklist, remove label

### 9 Copilot Agent Personas

Specialized agent configurations in `.github/agents/` guide Copilot's behavior based on the type of work:

| Agent            | Role                                                   |
| ---------------- | ------------------------------------------------------ |
| Senior Developer | End-to-end feature implementation with tests           |
| AI Engineer      | LLM prompts, text-to-SQL, Bedrock integration          |
| Data Scientist   | ML models, feature engineering, statistical validation |
| Test Engineer    | Test coverage, edge cases, async endpoint tests        |
| Bug Fixer        | Minimal targeted fixes with regression tests           |
| Security Auditor | OWASP checks, bandit/pip-audit findings                |
| Code Reviewer    | BASSPC review methodology on PRs                       |
| Docs Writer      | README, architecture docs, API docs                    |
| Technical PM     | Issue triage, epic breakdown, acceptance criteria      |

## Agile Process

### Epic-Driven Planning

Work was organized into 19 epics, each a GitHub issue with a checklist of child issues:

1. Data Foundation
2. Scoring Engine
3. Evidence Graph
4. AI Reasoning Layer
5. API Layer
6. Claims Simulator UI
7. Chat Sidebar
8. CI/CD Pipeline
9. Documentation & Deliverables
10. EKS Migration
11. Real-time Claims Scoring Engine
12. User Personas & Investigation Workflow
13. Competition Hardening
14. UI & Responsive Design Fixes
15. Frontend V2 Stabilization
16. Unified CI/CD Pipeline
17. App-Level Authentication (JWT + RBAC)
18. Hackathon Gap Analysis
19. Test Coverage 90%+

### Issue Labels

Issues are categorized with two label dimensions:

**Phase labels** (pipeline stage):
`phase:0-spine`, `phase:1-data`, `phase:2-engine`, `phase:3-ai`, `phase:4-ui`, `phase:5-ship`

**Track labels** (component):
`backend`, `frontend`, `data`, `ai`, `infra`, `docs`

**Priority labels:**
`P0-critical`, `P1-important`, `P2-nice`

**Workflow:**
`in-progress`, `epic`, `story`

### Daily Scoreboards

Every day during the sprint, a scoreboard was published in `docs/agile/` tracking:

- Issues opened vs closed
- PRs merged
- CI pass rate
- Blockers and decisions

### One Issue, One PR

Strict rule: every PR closes exactly one issue. No batching. This kept the review cycle fast and the git history clean.

## CI/CD Pipeline

All code flows through a single unified workflow (`.github/workflows/pipeline.yml`).

### On Pull Request

```
Gate → Security ─┐
                 ├→ Build → Scan
Quality Backend ─┘
Quality Frontend ┘
```

| Stage                | What it does                                                                               | Blocks merge?      |
| -------------------- | ------------------------------------------------------------------------------------------ | ------------------ |
| **Gate**             | Validates PR title matches conventional commit format                                      | Yes                |
| **Security**         | gitleaks (secret scanning) + bandit (SAST) + pip-audit (Python CVEs) + npm audit (JS CVEs) | Yes                |
| **Quality Backend**  | ruff lint + ruff format + mypy type check + pytest with 95% coverage threshold             | Yes                |
| **Quality Frontend** | eslint + TypeScript check + vitest with 80% line coverage + vite build                     | Yes                |
| **Build**            | Docker images (linux/amd64) + CycloneDX SBOMs (backend + frontend)                         | Yes                |
| **Scan**             | Trivy vulnerability scan on both container images                                          | No (informational) |

### On Merge to Main (additional stages)

| Stage       | What it does                                                             |
| ----------- | ------------------------------------------------------------------------ |
| **Release** | Push Docker images to ECR with `:sha` + `:latest` tags                   |
| **Deploy**  | Update image tags in `precise-manifests` repo → ArgoCD auto-syncs to EKS |

### GitOps Deployment Model

```
Developer pushes to main
  → pipeline.yml builds + pushes images to ECR
  → Deploy job clones precisesoft/precise-manifests
  → Updates image SHA tags in k8s/cms-fraud/*.yaml
  → Pushes to precise-manifests
  → ArgoCD detects change, syncs to EKS cluster
  → kubectl rollout status confirms healthy deployment
```

Two separate repos:

- **`precisesoft/cms-fraud-detection`** — application code, CI/CD pipeline
- **`precisesoft/precise-manifests`** — Kubernetes manifests (ArgoCD source of truth)

### Infrastructure as Code

Terraform manages AWS resources separately via `.github/workflows/terraform.yml`:

- **Plan** on PR (paths: `terraform/**`)
- **Apply** on merge to main
- State stored in S3 (`cms-fraud-terraform-state`) with DynamoDB locking

Resources managed: ECR repositories, IAM roles, and related AWS infrastructure.

### Security Tooling Summary

| Tool      | Purpose                                | Stage    |
| --------- | -------------------------------------- | -------- |
| gitleaks  | Secret detection in git history        | Security |
| bandit    | Python static analysis (SAST)          | Security |
| pip-audit | Python dependency CVE scanning         | Security |
| npm audit | JavaScript dependency CVE scanning     | Security |
| CycloneDX | SBOM generation (backend + frontend)   | Build    |
| Trivy     | Container image vulnerability scanning | Scan     |

## Development Environment

### Local Setup

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ml]"

# Frontend
cd frontend && npm install
```

### Local CI Verification

Run before every push:

```bash
# Backend
ruff check src/ tests/ && ruff format --check src/ tests/
mypy src/
pytest --cov=src --cov-report=term -q

# Frontend
cd frontend
npm run lint && npx tsc --noEmit && npm test && npm run build
```

### Docker

```bash
docker compose up -d    # Starts PostgreSQL, Neo4j, API, Frontend
docker compose logs -f  # Monitor all services
```
