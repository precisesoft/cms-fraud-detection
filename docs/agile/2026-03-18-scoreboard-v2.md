# Sprint Scoreboard — 2026-03-18 (Evening Update)

**Target**: CMS AI Hackathon submission — March 25, 2026 (7 days remaining)

## Summary

Backend API is complete — all 10 data endpoints live, tested, merged. The full Neo4j evidence graph pipeline shipped today: client wrapper, projection script, and API endpoint. Path to CMS Pilot briefing done. New Epic #112 created to migrate from forge k3s to Precise Software Factory EKS cluster (already validated: EKS access, ArgoCD, ECR, Bedrock all confirmed working). Bedrock access unlocks the AI layer. Critical path: Terraform + EKS deployment, then frontend.

## Scoreboard

| Phase                   | Closed | Total  | % Done  | Status                                                |
| ----------------------- | ------ | ------ | ------- | ----------------------------------------------------- |
| 0: Spine (CI/CD)        | 10     | 14     | 71%     | Core CI done, Dockerfiles + frontend CI remaining     |
| 1: Data Foundation      | 10     | 11     | 91%     | Neo4j done, only ETL test remaining                   |
| 2: Scoring Engine + API | 16     | 17     | 94%     | All data endpoints live, only chat endpoint remaining |
| 3: AI Intelligence      | 0      | 9      | 0%      | Bedrock access confirmed — unblocked                  |
| 4: UI                   | 0      | 19     | 0%      | Not started — biggest risk                            |
| 5: Ship (Docs + Deploy) | 5      | 10     | 50%     | Pilot briefing + methodology + responsible AI shipped |
| 10: EKS Migration (NEW) | 0      | 11     | 0%      | Pre-reqs validated, issues created, ready to execute  |
| **Total**               | **41** | **91** | **45%** |                                                       |

## What Shipped Today (Mar 18 evening session)

- **PR #107** — `GET /api/dashboard` + `GET /api/dashboard/heatmap` (#101, #102)
- **PR #108** — Path to CMS Pilot 5-min briefing (#57)
- **PR #109** — Neo4j docker-compose + async client wrapper (#103)
- **PR #110** — Neo4j projection pipeline PostgreSQL → Neo4j (#104)
- **PR #111** — `GET /api/graph/{npi}` evidence graph endpoint (#105)

**5 PRs merged. 208 tests, 74% coverage. 10 live endpoints.**

## API Surface (10 endpoints)

| Endpoint                           | Method | PR   | Status      |
| ---------------------------------- | ------ | ---- | ----------- |
| `GET /health`                      | GET    | #88  | Live        |
| `GET /api/providers`               | GET    | #88  | Live        |
| `GET /api/providers/{npi}`         | GET    | #88  | Live        |
| `GET /api/providers/{npi}/signals` | GET    | #99  | Live        |
| `GET /api/providers/{npi}/peers`   | GET    | #99  | Live        |
| `GET /api/claims`                  | GET    | #97  | Live        |
| `POST /api/score`                  | POST   | #96  | Live        |
| `GET /api/fairness`                | GET    | #98  | Live        |
| `GET /api/dashboard`               | GET    | #107 | Live (NEW)  |
| `GET /api/dashboard/heatmap`       | GET    | #107 | Live (NEW)  |
| `GET /api/graph/{npi}`             | GET    | #111 | Live (NEW)  |
| `POST /api/chat`                   | POST   | —    | Not started |

## Epic Status

| Epic                    | Status     | Stories    | Notes                                          |
| ----------------------- | ---------- | ---------- | ---------------------------------------------- |
| #1 Data Foundation      | Open       | 10/11 done | Only ETL test (#22) remaining                  |
| #2 Scoring Engine       | **CLOSED** | 5/5 done   | 100% coverage                                  |
| #3 Evidence Graph       | Open       | 3/4 done   | Backend complete, only frontend viz (#66) left |
| #4 AI Reasoning         | Open       | 0/7 done   | Bedrock access confirmed — unblocked now       |
| #5 API Layer            | Open       | 11/12 done | Only chat endpoint (#32) remaining             |
| #6 Claims Simulator UI  | Open       | 0/7 done   | Blocked on frontend scaffold                   |
| #7 Chat Sidebar         | Open       | 0/6 done   | Blocked on AI layer                            |
| #8 CI/CD Pipeline       | Open       | 10/14 done | Dockerfiles + frontend CI remaining            |
| #9 Documentation        | Open       | 5/8 done   | Pilot + methodology + responsible AI shipped   |
| #10 EKS Migration (NEW) | Open       | 0/11 done  | Pre-reqs validated, Terraform track planned    |

## EKS Migration Pre-Requisites (all validated)

- AWS CLI v2.34.11 installed, `precise-eng` profile working
- EKS cluster: `508aas-platform-dev-cluster` (1 node, v1.32)
- ArgoCD: running, `precise-manifests` repo connected
- ECR: available for image repos
- Storage: gp3 (EBS CSI) default
- Bedrock: Claude Sonnet 4.6, Opus 4.6, Haiku 4.5 all available
- kubectl access confirmed from megamind

## Test Coverage

| Module                        | Coverage            |
| ----------------------------- | ------------------- |
| `src/api/routes/claims.py`    | 100%                |
| `src/api/routes/dashboard.py` | 100%                |
| `src/api/routes/fairness.py`  | 100%                |
| `src/api/routes/graph.py`     | 97%                 |
| `src/api/routes/providers.py` | 94%                 |
| `src/api/routes/score.py`     | 98%                 |
| `src/api/routes/signals.py`   | 100%                |
| `src/api/schemas.py`          | 99%                 |
| `src/scoring/extract.py`      | 100%                |
| `src/scoring/score.py`        | 100%                |
| `src/scoring/taxonomy.py`     | 100%                |
| **Total**                     | **74%** (208 tests) |

## Critical Path (Updated)

| Day       | Must Ship                                                      | Nice to Have         |
| --------- | -------------------------------------------------------------- | -------------------- |
| Mar 18-19 | #122 TF scaffold, #118 state backend, #121 ECR, #13 Dockerfile | #119 IAM SA          |
| Mar 19-20 | #120 GH secrets, #116 CI push, #114 K8s manifests              | #41 Next.js scaffold |
| Mar 20-21 | #115 ArgoCD app, #117 data seed, #28 Bedrock client            | #29 Schema prompt    |
| Mar 21-22 | #41 Next.js, #42 Claims, #43 Provider detail, #59 Dashboard    | #44 Risk gauge       |
| Mar 22-23 | #30 Text-to-SQL, #31 Narrative, #32 Chat, #60 Heatmap          | #45 Peer chart       |
| Mar 23-24 | #47-49 Chat sidebar, #63 Fairness, #46 Scan button             | #34 AI testing       |
| Mar 24-25 | #70 Demo script, #106 Disclosure, polish, submission           | —                    |

## Risks

- **Frontend is 0%** — 19 stories, 7 days. Still the critical bottleneck.
- **EKS migration is new scope** — 11 issues added, but Terraform + k8s can move fast.
- **AI layer is 0%** — but now unblocked (Bedrock access confirmed).
- **Solo execution pressure** — lots of parallel tracks (infra + frontend + AI).
