# Sprint Scoreboard — 2026-03-20

**Target**: CMS AI Hackathon demo — March 27, 2026 (7 days remaining)

## Summary

Platform is 87% complete with all core features live on EKS. AI layer fully shipped: Bedrock text-to-SQL chat, risk narratives on scoring endpoints, and chat sidebar UI deployed. Readonly DB pool added for defense-in-depth on LLM-generated SQL. Conversation history now flows through for multi-turn follow-ups. Three chat UI issues (#47, #48, #49, #51) closed in one PR. CrashLoopBackOff on API pod fixed — was missing `DATABASE_URL_READONLY` env var in k8s deployment. All pods healthy, all CI green.

## Scoreboard

| Phase                   | Closed | Total  | % Done  | Status                                              |
| ----------------------- | ------ | ------ | ------- | --------------------------------------------------- |
| 0: Spine (CI/CD)        | 14     | 14     | 100%    | All CI/CD complete                                  |
| 1: Data Foundation      | 11     | 11     | 100%    | Complete                                            |
| 2: Scoring Engine + API | 17     | 17     | 100%    | All endpoints live including simulate + chat        |
| 3: AI Intelligence      | 7      | 9      | 78%     | Core done — chart specs + AI testing remaining      |
| 4: UI                   | 18     | 21     | 86%     | Chat sidebar shipped — investigation view remaining |
| 5: Ship (Docs + Deploy) | 5      | 10     | 50%     | Demo script + disclosures remaining                 |
| 10: EKS Migration       | 12     | 12     | 100%    | Complete                                            |
| 11: Real-time Scoring   | 7      | 7      | 100%    | Complete                                            |
| 12: Investigation WF    | 0      | 4      | 0%      | Not started — P0 for demo                           |
| **Total**               | **83** | **95** | **87%** |                                                     |

## What Shipped (Mar 19-20)

- **PR #158** — Bedrock client wrapper + schema/few-shot prompts (#28, #29)
- **PR #159** — Text-to-SQL engine with query validation (#30)
- **PR #160** — Risk narrative generator wired into scoring (#31)
- **PR #161** — Chat endpoint `POST /api/chat` (#32)
- **PR #162** — AI hardening: readonly pool, conversation history, improved logging
- **PR #163** — Chat sidebar UI: Sheet panel, suggestions, SQL details (#47, #48, #49, #51)
- Deployed all changes to EKS — API and frontend pods restarted with latest images
- Fixed CrashLoopBackOff: patched API deployment with `DATABASE_URL_READONLY` env var

**6 PRs merged. 252 tests, 73% coverage. 12 live endpoints. AI chat live.**

## API Surface (12 endpoints)

| Endpoint                           | Method | PR   | Status |
| ---------------------------------- | ------ | ---- | ------ |
| `GET /health`                      | GET    | #88  | Live   |
| `GET /api/providers`               | GET    | #88  | Live   |
| `GET /api/providers/{npi}`         | GET    | #88  | Live   |
| `GET /api/providers/{npi}/signals` | GET    | #99  | Live   |
| `GET /api/providers/{npi}/peers`   | GET    | #99  | Live   |
| `GET /api/claims`                  | GET    | #97  | Live   |
| `POST /api/score`                  | POST   | #96  | Live   |
| `POST /api/claims/simulate`        | POST   | #157 | Live   |
| `GET /api/fairness`                | GET    | #98  | Live   |
| `GET /api/dashboard`               | GET    | #107 | Live   |
| `GET /api/dashboard/heatmap`       | GET    | #107 | Live   |
| `GET /api/graph/{npi}`             | GET    | #111 | Live   |
| `POST /api/chat`                   | POST   | #161 | Live   |

## Live Platform Stats

| Metric        | Value  |
| ------------- | ------ |
| Providers     | 10,282 |
| Cases scored  | 13,225 |
| High-risk     | 153    |
| Review        | 5,226  |
| Stable        | 4,903  |
| Tests passing | 252    |
| Code coverage | 73%    |
| API pods      | 2      |
| Frontend pods | 2      |

## Epic Status

| Epic                       | Status     | Stories    | Notes                                              |
| -------------------------- | ---------- | ---------- | -------------------------------------------------- |
| #1 Data Foundation         | **CLOSED** | 11/11 done | Complete                                           |
| #2 Scoring Engine          | **CLOSED** | 5/5 done   | 100% coverage                                      |
| #3 Evidence Graph          | **CLOSED** | 4/4 done   | Backend + frontend viz complete                    |
| #4 AI Reasoning            | Open       | 7/9 done   | Chart specs (#33) + AI testing (#34) remaining     |
| #5 API Layer               | **CLOSED** | 12/12 done | All endpoints live                                 |
| #6 Claims Simulator UI     | **CLOSED** | 7/7 done   | Complete with AI narrative                         |
| #7 Chat Sidebar            | Open       | 4/6 done   | Core done, chart renderer (#50) + SSE (#65) remain |
| #8 CI/CD Pipeline          | **CLOSED** | 14/14 done | All gates active                                   |
| #9 Documentation           | Open       | 5/8 done   | Demo script + disclosures remaining                |
| #10 EKS Migration          | **CLOSED** | 12/12 done | Complete                                           |
| #11 Real-time Scoring      | **CLOSED** | 7/7 done   | Complete                                           |
| #12 Investigation Workflow | Open       | 0/4 done   | Not started — P0 for demo                          |

## Infrastructure Status

| Component  | Status  | Details                                                             |
| ---------- | ------- | ------------------------------------------------------------------- |
| API        | Healthy | 2 pods, 0 restarts, readonly pool active                            |
| Frontend   | Healthy | 2 pods, chat sidebar deployed                                       |
| PostgreSQL | Healthy | StatefulSet, 20Gi gp3                                               |
| Neo4j      | Healthy | StatefulSet, 10Gi gp3                                               |
| CI/CD      | Green   | 7 pipelines (lint, type, test, secrets, security, PR title, deploy) |
| Bedrock    | Active  | Haiku 4.5 (chat), Sonnet 4.6 (narratives)                           |

## AI Layer Architecture

| Component   | Model                                    | Purpose                        |
| ----------- | ---------------------------------------- | ------------------------------ |
| Text-to-SQL | `us.anthropic.claude-haiku-4-5-20251001` | NL → validated SQL → results   |
| Narratives  | `us.anthropic.claude-sonnet-4-6`         | Risk investigation briefs      |
| Safety      | Regex validation + readonly DB user      | SELECT-only, 5s timeout, LIMIT |
| History     | Last 3 turns (6 messages)                | Multi-turn follow-up context   |

## Remaining Work (Priority Order)

### P0 — Must have for demo

| Issue | Title                                        | Estimate |
| ----- | -------------------------------------------- | -------- |
| #149  | Investigation workflow — case status actions | 1 day    |
| #70   | Write demo script and rehearse (5-7 min)     | 0.5 day  |

### P1 — Should have

| Issue | Title                                       | Estimate |
| ----- | ------------------------------------------- | -------- |
| #33   | Chart spec generator (AI → Recharts config) | 0.5 day  |
| #34   | Test AI layer with 20+ questions            | 0.5 day  |
| #50   | Inline chart renderer for AI responses      | 0.5 day  |
| #147  | Claims inbox — prioritized queue            | 1 day    |
| #150  | Unified investigation view (deep-dive)      | 1 day    |
| #69   | Judge access to private repo                | 0.5 day  |
| #106  | AI tool usage and open-source disclosure    | 0.5 day  |

### P2 — Cut if needed

| Issue | Title                          |
| ----- | ------------------------------ |
| #61   | Time-series trend charts       |
| #65   | Streaming chat responses (SSE) |
| #151  | Activity log / audit trail     |

## Risks

- **Investigation workflow is 0%** — #149 is P0 and the only major feature gap for a credible demo.
- **Demo script not written** — #70 needs real rehearsal time, not just a document.
- **7 days left** — enough for remaining P0s + some P1s, but no room for surprises.
- **Solo execution** — all tracks (backend, frontend, AI, infra, docs) on one person.

## Velocity

| Period    | PRs Merged | Issues Closed |
| --------- | ---------- | ------------- |
| Mar 12-16 | 15         | 21            |
| Mar 16-18 | 15         | 24            |
| Mar 18-19 | 12         | 18            |
| Mar 19-20 | 6          | 10            |
| **Total** | **48**     | **83**        |
