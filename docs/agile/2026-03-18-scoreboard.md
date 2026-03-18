# Sprint Scoreboard — 2026-03-18

**Target**: CMS AI Hackathon submission — March 25, 2026 (7 days remaining)

## Summary

Backend API is effectively complete — all 6 data endpoints are live, tested, and merged. Scoring engine is done with 100% coverage. CI/CD pipeline has 7 automated checks. Two critical judge-facing documents (risk methodology, responsible AI) are shipped. The critical path now runs through Phase 3 (AI layer) and Phase 4 (frontend UI). Phase 4 is 0% — this is the biggest risk.

## Scoreboard

| Phase                   | Closed | Total  | % Done  | Status                                           |
| ----------------------- | ------ | ------ | ------- | ------------------------------------------------ |
| 0: Spine (CI/CD)        | 10     | 14     | 71%     | Core CI done, Dockerfiles + frontend CI deferred |
| 1: Data Foundation      | 7      | 11     | 64%     | Pipeline done, Neo4j + ETL test remaining        |
| 2: Scoring Engine + API | 13     | 14     | 93%     | 1 epic open (API layer), all stories closed      |
| 3: AI Intelligence      | 0      | 9      | 0%      | Not started — needs Bedrock setup                |
| 4: UI                   | 0      | 19     | 0%      | Not started — biggest risk                       |
| 5: Ship (Docs + Deploy) | 3      | 10     | 30%     | Key docs done, demo script + k8s remaining       |
| **Total**               | **33** | **77** | **43%** |                                                  |

_Note: 30 closed issues + 3 closed (epic #2, #90, #81 docs) = 33 tracked items. 30 open issues + 9 open epics + 8 non-epic open = varies by counting. Epics excluded from totals above — only stories counted._

## By Priority

| Priority     | Closed | Total | % Done |
| ------------ | ------ | ----- | ------ |
| P0-critical  | 23     | 30    | 77%    |
| P1-important | 7      | 19    | 37%    |
| P2-nice      | 3      | 5     | 60%    |

## Epic Status

| Epic                   | Status     | Child Stories | Notes                                  |
| ---------------------- | ---------- | ------------- | -------------------------------------- |
| #1 Data Foundation     | Open       | 7/9 done      | Neo4j (#21) + ETL test (#22) remaining |
| #2 Scoring Engine      | **CLOSED** | 5/5 done      | 100% coverage, all signals tested      |
| #3 Evidence Graph      | Open       | 0/2 done      | Neo4j deferred                         |
| #4 AI Reasoning        | Open       | 0/7 done      | Blocked on Bedrock setup               |
| #5 API Layer           | Open       | 7/8 done      | Only chat endpoint remaining           |
| #6 Claims Simulator UI | Open       | 0/7 done      | Blocked on frontend scaffold           |
| #7 Chat Sidebar        | Open       | 0/6 done      | Blocked on AI layer                    |
| #8 CI/CD Pipeline      | Open       | 10/14 done    | Phase 4 deferred (Docker, k8s, ArgoCD) |
| #9 Documentation       | Open       | 3/8 done      | Methodology + responsible AI shipped   |

## What Shipped Since Last Scoreboard (Mar 16 → Mar 18)

- **PR #88** — `/api/providers` list + detail (with risk band computation)
- **PR #91** — Signal taxonomy with 13 signals, z-score tiers, point system
- **PR #92** — Signal extraction module (maps case rows to fired signals)
- **PR #93** — Risk + legitimacy score computation with case labeling
- **PR #95** — Stale docs sweep (README, Dockerfile, pyproject.toml, CONTRIBUTING)
- **PR #96** — `/api/score` on-the-fly scoring endpoint
- **PR #97** — `/api/claims` with pagination, 6 filters
- **PR #98** — `/api/fairness` flagging rate analysis (state + specialty)
- **PR #99** — `/api/providers/{npi}/signals` + `/api/providers/{npi}/peers`
- **PR #100** — Risk scoring methodology + responsible AI docs

**10 PRs merged in 2 days.** All CI green. 158 tests, 78% code coverage.

## API Surface Complete

| Endpoint                           | Method | PR  | Status      |
| ---------------------------------- | ------ | --- | ----------- |
| `GET /health`                      | GET    | #88 | Live        |
| `GET /api/providers`               | GET    | #88 | Live        |
| `GET /api/providers/{npi}`         | GET    | #88 | Live        |
| `GET /api/providers/{npi}/signals` | GET    | #99 | Live        |
| `GET /api/providers/{npi}/peers`   | GET    | #99 | Live        |
| `GET /api/claims`                  | GET    | #97 | Live        |
| `POST /api/score`                  | POST   | #96 | Live        |
| `GET /api/fairness`                | GET    | #98 | Live        |
| `POST /api/chat`                   | POST   | —   | Not started |

## Test Coverage

| Module                        | Coverage            |
| ----------------------------- | ------------------- |
| `src/api/routes/claims.py`    | 100%                |
| `src/api/routes/fairness.py`  | 100%                |
| `src/api/routes/providers.py` | 94%                 |
| `src/api/routes/score.py`     | 98%                 |
| `src/api/routes/signals.py`   | 100%                |
| `src/api/schemas.py`          | 99%                 |
| `src/scoring/extract.py`      | 100%                |
| `src/scoring/score.py`        | 100%                |
| `src/scoring/taxonomy.py`     | 100%                |
| **Total**                     | **78%** (158 tests) |

## Critical Path to Submission (7 days)

| Day       | Must Ship                                             | Nice to Have      |
| --------- | ----------------------------------------------------- | ----------------- |
| Mar 18-19 | #41 Scaffold Next.js, #28 Bedrock client              | #29 Schema prompt |
| Mar 19-20 | #42 Claims table, #43 Provider detail, #59 Dashboard  | #44 Risk gauge    |
| Mar 20-21 | #30 Text-to-SQL, #31 Narrative gen, #32 Chat endpoint | #33 Chart spec    |
| Mar 21-22 | #47-49 Chat sidebar, #60 Heatmap, #63 Fairness view   | #45 Peer chart    |
| Mar 22-23 | #46 Scan button, #57 Path to Pilot briefing           | #34 AI testing    |
| Mar 23-24 | #70 Demo script + rehearsal, #58 Disclosures          | #13 Dockerfiles   |
| Mar 24-25 | Final polish, bug fixes, submission                   | —                 |

## Risks

- **Frontend is 0%** — 19 stories, 7 days. This is the critical bottleneck.
- **AI layer is 0%** — Bedrock not set up yet. Text-to-SQL + narrative gen are demo highlights.
- **kubectl still broken** — curl workaround works but slows k8s deployment.
- **Solo execution** — Bibek has parallel tasks but frontend is mostly solo work.
