# Argus Scorecard — 2026-03-23

> CMS AI Hackathon | Proactive Medicare Provider Fraud Detection with Explainable AI

---

## Project Summary

| Metric                | Value       |
| --------------------- | ----------- |
| Total issues          | 155         |
| Leaf issues (pointed) | 139         |
| Epics (containers)    | 16          |
| Issues closed         | 144 (92.9%) |
| Issues open           | 11          |
| Total story points    | 509 SP      |
| Merged PRs            | 117         |
| Lines added           | 46,920      |
| Lines deleted         | 18,208      |
| Test files            | 27          |
| Tests collected       | 124         |
| API endpoints         | 18          |
| Providers in DB       | 10,282      |
| Cases scored          | 13,225      |
| Detection rate        | 91.3%       |

---

## Daily Scoreboard

| Date       | Day | Created | Closed | SP Delivered | PRs Merged | AI PRs | Cum SP | Cum Closed | % Done |
| ---------- | --- | ------- | ------ | ------------ | ---------- | ------ | ------ | ---------- | ------ |
| 2026-03-15 | 1   | 70      | 0      | 0            | 0          | 0      | 0      | 0          | 0%     |
| 2026-03-16 | 2   | 0       | 11     | 40           | 0          | 0      | 40     | 11         | 15%    |
| 2026-03-17 | 3   | 8       | 12     | 28           | 13         | 0      | 68     | 23         | 29%    |
| 2026-03-18 | 4   | 18      | 40     | 150          | 26         | 0      | 218    | 63         | 65%    |
| 2026-03-19 | 5   | 11      | 23     | 73           | 17         | 0      | 291    | 86         | 80%    |
| 2026-03-20 | 6   | 29      | 32     | 110          | 38         | 8      | 401    | 118        | 86%    |
| 2026-03-21 | 7   | 8       | 14     | 55           | 10         | 3      | 456    | 132        | 91%    |
| 2026-03-22 | 8   | 0       | 8      | 17           | 8          | 7      | 473    | 140        | 97%    |
| 2026-03-23 | 9   | 11      | 5      | 20           | 6          | 5      | 493    | 145        | 93%    |

**Peak velocity**: Day 4 (Mar 18) -- 40 issues closed, 150 SP delivered, 26 PRs merged.
**AI agent introduced**: Day 6 (Mar 20) -- first autonomous PRs merged. By Day 8, AI PRs outnumbered human PRs.

---

## Story Points by Phase

| Phase                    | Issues  | Closed  | % Done  | Total SP | Copilot CLI SP | Agent SP | Agent Issues |
| ------------------------ | ------- | ------- | ------- | -------- | -------------- | -------- | ------------ |
| 0: Spine / CI-CD         | 18      | 15      | 83%     | 45       | 45             | 0        | 0            |
| 1: Data Foundation       | 12      | 12      | 100%    | 50       | 50             | 0        | 0            |
| 2: Scoring Engine + API  | 18      | 18      | 100%    | 74       | 74             | 0        | 0            |
| 3: AI Reasoning Layer    | 16      | 16      | 100%    | 85       | 79             | 6        | 2            |
| 4: Frontend UI           | 36      | 34      | 94%     | 138      | 106            | 32       | 10           |
| 5: Ship / Infra / Docs   | 36      | 35      | 97%     | 104      | 101            | 3        | 3            |
| Cross-cutting (descoped) | 2       | 2       | 100%    | 10       | 10             | 0        | 0            |
| **Total**                | **139** | **132** | **95%** | **509**  | **468**        | **41**   | **15**       |

---

## AI-Driven Development Model

**100% of the code was AI-generated.** The human contribution was architecture, decisions, orchestration, and quality review. The project transitioned through two AI development modes:

### Development Modes

| Mode                         | Tool                     | PRs     | SP      | Lines Added | Human Role                                                   |
| ---------------------------- | ------------------------ | ------- | ------- | ----------- | ------------------------------------------------------------ |
| AI-assisted pair programming | GitHub Copilot CLI       | 95      | 468     | 43,261      | Coding with AI autocomplete, prompts, and inline suggestions |
| Fully autonomous agent       | GitHub Copilot SWE Agent | 22      | 41      | 3,659       | Orchestrator only -- assign issue, review PR, merge          |
| **Total**                    |                          | **117** | **509** | **46,920**  |                                                              |

### How It Worked

**Phases 0-3 (Copilot CLI):** Two developers (Arun Sanna, Bibek Poudel) worked in VS Code with GitHub Copilot providing inline code suggestions, function completions, and test generation. The AI wrote the code; the humans guided direction, reviewed output, and made architectural decisions.

**Phases 4-5 (Copilot SWE Agent):** Transitioned to fully autonomous workflow. The human orchestrators:

1. Created GitHub issues with acceptance criteria
2. Assigned issues to `copilot-swe-agent`
3. Agent autonomously created branches, wrote code, opened PRs
4. Humans reviewed PRs using BASSPC methodology, requested fixes
5. Agent self-corrected, humans approved and merged

### AI Contribution Summary

| Metric                  | Value        | Note                                                  |
| ----------------------- | ------------ | ----------------------------------------------------- |
| AI-generated code       | 100%         | All 46,920 lines written by AI (Copilot CLI or Agent) |
| AI-autonomous PRs       | 22 (18.8%)   | Fully autonomous -- no human coding                   |
| AI-assisted PRs         | 95 (81.2%)   | Human-directed, AI-generated via Copilot CLI          |
| Human-equivalent effort | ~650-800 hrs | Based on SP-to-hours industry benchmarks              |
| Actual calendar time    | ~2 weeks     | Two engineers + AI, full-stack delivery               |

### SP-to-Hours Benchmark

| SP  | Est. Human Hours | Issues  | Total Hours       |
| --- | ---------------- | ------- | ----------------- |
| 1   | 0.5 - 1 hr       | 15      | 8 - 15            |
| 2   | 1 - 2 hrs        | 27      | 27 - 54           |
| 3   | 2 - 4 hrs        | 40      | 80 - 160          |
| 5   | 4 - 8 hrs        | 47      | 188 - 376         |
| 8   | 8 - 16 hrs       | 9       | 72 - 144          |
| 13  | 16 - 24 hrs      | 1       | 16 - 24           |
|     |                  | **139** | **391 - 773 hrs** |

---

## Story Point Distribution

| SP  | Label | Count   | Points  | Description                         |
| --- | ----- | ------- | ------- | ----------------------------------- |
| 1   | sp:1  | 15      | 15      | Trivial -- one-line fix, config     |
| 2   | sp:2  | 27      | 54      | Small -- single file, clear scope   |
| 3   | sp:3  | 40      | 120     | Medium -- 2-3 files, some logic     |
| 5   | sp:5  | 47      | 235     | Large -- new feature, multi-file    |
| 8   | sp:8  | 9       | 72      | Complex -- new system/module        |
| 13  | sp:13 | 1       | 13      | Epic-level -- multi-component study |
|     |       | **139** | **509** |                                     |

---

## Autonomous Agent Issues (Copilot SWE Agent)

| Issue | Title                           | SP  | PR   | Phase |
| ----- | ------------------------------- | --- | ---- | ----- |
| #150  | Unified investigation view      | 8   | #243 | 4     |
| #190  | Enrich /score narrative context | 5   | #230 | 3     |
| #192  | Investigation inbox page        | 5   | #241 | 4     |
| #193  | Fix heatmap state filter        | 2   | #240 | 4     |
| #194  | Provider filter controls        | 3   | #242 | 4     |
| #203  | Fix ChatMessage.role validation | 1   | #216 | 3     |
| #251  | Collapsible sidebar (mobile)    | 5   | #257 | 4     |
| #252  | Table horizontal scroll         | 1   | #260 | 4     |
| #253  | Unicode KPI fix                 | 1   | #263 | 4     |
| #254  | Responsive provider header      | 2   | #261 | 4     |
| #255  | Fairness chart label clipping   | 2   | #264 | 4     |
| #256  | Responsive investigate buttons  | 3   | #262 | 4     |
| #186  | Update responsible AI doc       | 1   | #205 | 5     |
| #195  | Judge Resources in README       | 2   | #204 | 5     |
| #196  | Fix version inconsistencies     | 1   | #200 | 5     |

---

## Epic Status

| Epic | Title                     | Children | Closed | Status   |
| ---- | ------------------------- | -------- | ------ | -------- |
| #1   | Data Foundation           | 11       | 11     | CLOSED   |
| #2   | Scoring Engine            | 5        | 5      | CLOSED   |
| #3   | Evidence Graph            | 4        | 4      | CLOSED   |
| #4   | AI Reasoning Layer        | 9        | 9      | CLOSED   |
| #5   | API Layer                 | 12       | 12     | CLOSED   |
| #6   | Claims Simulator UI       | 7        | 7      | CLOSED   |
| #7   | Chat Sidebar              | 6        | 6      | CLOSED   |
| #8   | CI/CD Pipeline            | 14       | 14     | CLOSED   |
| #9   | Documentation             | 8        | 5      | **OPEN** |
| #112 | EKS Migration             | 12       | 12     | CLOSED   |
| #141 | Real-time Scoring         | 7        | 7      | CLOSED   |
| #142 | Investigation Workflow    | 4        | 4      | CLOSED   |
| #197 | Competition Hardening     | varies   | varies | **OPEN** |
| #250 | UI & Responsive Design    | 6        | 6      | CLOSED   |
| #271 | Frontend V2 Stabilization | 4        | 1      | **OPEN** |
| #273 | Unified CI/CD Pipeline    | 4        | 2      | **OPEN** |

---

## Architecture

| Component      | Technology                           | Deployment            |
| -------------- | ------------------------------------ | --------------------- |
| API            | FastAPI + async psycopg pool         | EKS, 2 replicas       |
| Frontend       | Next.js 16 + Tailwind v4 + shadcn/ui | EKS, 2 replicas       |
| Database       | PostgreSQL 16                        | EKS StatefulSet, 20Gi |
| Graph          | Neo4j 5 Community                    | EKS StatefulSet, 10Gi |
| AI (chat)      | Claude Haiku 4.5 via Bedrock         | us-east-1             |
| AI (narrative) | Claude Sonnet 4.6 via Bedrock        | us-east-1             |
| ML             | Isolation Forest (scikit-learn)      | Bundled in API image  |
| CI/CD          | GitHub Actions + ArgoCD              | 7 workflows           |
| Infra          | Terraform + EKS                      | us-east-1             |
| Domain         | argus.precise-lab.com                | Route53 + Istio NLB   |

---

## Scoring Signals (14)

1. high_avg_charge
2. high_bene_count
3. cross_state_billing
4. high_unique_services
5. high_per_bene_charge
6. outlier_charge_per_service
7. high_case_count
8. high_distinct_hcpcs
9. high_charge_variance
10. specialty_mismatch
11. outlier_bene_per_case
12. geographic_spread
13. network_risk
14. concentration_outlier

---

## Validation Results

| Metric                        | Value |
| ----------------------------- | ----- |
| Overall blind detection rate  | 91.3% |
| Billing abuse (424.535(A)(8)) | 94%   |
| Felony revocations            | 100%  |
| Non-revoked baseline flagged  | 51.4% |
| Revoked NPIs tested           | 335   |
| Revoked cases in test set     | 862   |

---

## API Surface (18 endpoints)

| Endpoint                           | Method | Purpose                 |
| ---------------------------------- | ------ | ----------------------- |
| `GET /health`                      | GET    | Health check            |
| `GET /api/providers`               | GET    | Provider list + search  |
| `GET /api/providers/{npi}`         | GET    | Provider detail         |
| `GET /api/providers/{npi}/signals` | GET    | Signal breakdown        |
| `GET /api/providers/{npi}/peers`   | GET    | Peer comparison         |
| `GET /api/claims`                  | GET    | Claims with pagination  |
| `POST /api/score`                  | POST   | Score a provider        |
| `POST /api/claims/simulate`        | POST   | Simulate new claim      |
| `GET /api/fairness`                | GET    | Fairness analysis       |
| `GET /api/dashboard`               | GET    | Dashboard KPIs          |
| `GET /api/dashboard/heatmap`       | GET    | Geographic risk map     |
| `GET /api/graph/{npi}`             | GET    | Evidence graph          |
| `POST /api/chat`                   | POST   | AI text-to-SQL chat     |
| `GET /api/validation`              | GET    | Detection rate stats    |
| `GET /api/network-risk/{npi}`      | GET    | Network risk signal     |
| `GET /api/anomaly/{npi}`           | GET    | Isolation forest scores |
| `GET /api/investigation/queue`     | GET    | Investigation inbox     |
| `POST /api/investigation/actions`  | POST   | Case status actions     |

---

## CI/CD Pipelines (7)

| Workflow          | Trigger   | Jobs                              |
| ----------------- | --------- | --------------------------------- |
| `ci.yml`          | PR        | ruff lint, mypy typecheck, pytest |
| `ci-frontend.yml` | PR        | eslint, tsc, next build           |
| `pr-title.yml`    | PR        | Conventional commit format        |
| `secrets.yml`     | PR        | Gitleaks scan                     |
| `security.yml`    | PR        | pip-audit CVEs, bandit SAST       |
| `sbom.yml`        | Push main | CycloneDX SBOM generation         |
| `deploy.yml`      | Push main | Docker build + ECR push           |

---

## Open Items (11 remaining)

| Issue | Title                                     | Type | SP  |
| ----- | ----------------------------------------- | ---- | --- |
| #9    | Epic 9: Documentation                     | Epic | --  |
| #69   | Judge access to private repo              | Leaf | 1   |
| #197  | Epic 13: Competition Hardening            | Epic | --  |
| #201  | Demo rehearsal with live EKS              | Leaf | 2   |
| #267  | Cleanup unused deps + .npmrc              | Leaf | 3   |
| #268  | Route-based code splitting                | Leaf | 3   |
| #269  | Fix ClaimDetail/InvestigationDetail fetch | Leaf | 2   |
| #270  | Deploy Vite frontend to EKS               | Leaf | 5   |
| #271  | Epic: Frontend V2 Stabilization           | Epic | --  |
| #273  | Epic: Unified CI/CD Pipeline              | Epic | --  |
| #276  | CI: Release + Deploy stages               | Leaf | 5   |
| #277  | Delete old workflows                      | Leaf | 3   |
