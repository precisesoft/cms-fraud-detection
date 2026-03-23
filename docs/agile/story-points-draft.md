# Story Points Classification — Draft for Review

> **Scale**: Fibonacci (1, 2, 3, 5, 8, 13)
> **Epics**: Not pointed (they are containers). Points are on leaf issues only.
> **Classification basis**: PR diff size, files touched, complexity of logic, number of integration points.

| SP  | Meaning                                      | Typical PR profile       |
| --- | -------------------------------------------- | ------------------------ |
| 1   | Trivial — one-line fix, typo, config tweak   | 1 file, <20 lines        |
| 2   | Small — single file, clear scope             | 1-2 files, 20-100 lines  |
| 3   | Medium — 2-3 files, some logic               | 2-4 files, 100-300 lines |
| 5   | Large — new feature, multi-file              | 4-8 files, 300-600 lines |
| 8   | Complex — new system/module                  | 8+ files, 600-1000 lines |
| 13  | Epic-level — infrastructure, multi-component | 10+ files, 1000+ lines   |

---

## Phase 0: Spine / CI/CD (Epic #8)

| Issue | Title                                  | PR   | Author | +/-      | Files | SP  | Rationale                         |
| ----- | -------------------------------------- | ---- | ------ | -------- | ----- | --- | --------------------------------- |
| #10   | Scaffold monorepo                      | —    | arun   | —        | —     | 3   | Initial project structure         |
| #11   | GitHub Actions CI (backend)            | #77  | arun   | +128/-40 | 8     | 3   | Multi-job workflow config         |
| #12   | GitHub Actions CI (frontend)           | #157 | arun   | +95/-25  | 2     | 3   | Lint + typecheck + build workflow |
| #13   | Multi-stage Dockerfiles                | #126 | arun   | +55/-4   | 3     | 3   | Backend + frontend Dockerfiles    |
| #14   | Branch protection + PR template        | #84  | arun   | +32/-0   | 1     | 1   | Config only                       |
| #68   | Env setup: .env + docker-compose       | —    | arun   | —        | —     | 2   | Config files                      |
| #71   | Security scanning (pip-audit + bandit) | #79  | arun   | +74/-0   | 2     | 2   | Workflow YAML                     |
| #72   | Dependabot config                      | #83  | arun   | +18/-0   | 1     | 1   | Single YAML file                  |
| #73   | Secrets scanning (gitleaks)            | #78  | arun   | +41/-0   | 2     | 1   | Single workflow                   |
| #74   | mypy type checking gate                | #80  | arun   | +44/-8   | 7     | 2   | Workflow + type fixes             |
| #75   | Conventional commit lint               | #85  | arun   | +36/-0   | 1     | 1   | Single workflow                   |
| #76   | SBOM generation (CycloneDX)            | #86  | arun   | +51/-0   | 2     | 2   | Workflow + config                 |
| #81   | CONTRIBUTING.md + CLAUDE.md            | #82  | arun   | +231/-1  | 3     | 3   | SDLC process docs                 |

**Phase 0 subtotal: 27 SP**

---

## Phase 1: Data Foundation (Epics #1, #3)

| Issue | Title                                   | PR   | Author | +/-     | Files | SP  | Rationale                      |
| ----- | --------------------------------------- | ---- | ------ | ------- | ----- | --- | ------------------------------ |
| #15   | PostgreSQL schema                       | —    | arun   | —       | —     | 3   | Schema design + init SQL       |
| #16   | DuckDB ingestion pipeline               | —    | arun   | —       | —     | 5   | New ETL pipeline               |
| #17   | Provider identity spine                 | —    | arun   | —       | —     | 5   | Feature engineering            |
| #18   | Peer baselines by specialty x geography | —    | arun   | —       | —     | 5   | Statistical computation        |
| #19   | Harvest signals + risk scores           | —    | arun   | —       | —     | 5   | Signal extraction pipeline     |
| #20   | Bulk load Parquet into PostgreSQL       | —    | arun   | —       | —     | 3   | Data loader                    |
| #21   | Project evidence graph into Neo4j       | —    | arun   | —       | —     | 5   | Graph projection               |
| #22   | ETL integration test                    | —    | arun   | —       | —     | 2   | Test suite                     |
| #67   | Demo data fixture                       | —    | arun   | —       | —     | 2   | Test data setup                |
| #103  | Neo4j docker-compose + async client     | #109 | arun   | +512/-9 | 8     | 5   | New infra + client wrapper     |
| #104  | Neo4j projection pipeline               | #110 | arun   | +414/-0 | 2     | 5   | PG → Neo4j ETL                 |
| #105  | GET /api/graph/{npi}                    | #111 | arun   | +476/-0 | 4     | 5   | New API endpoint + graph query |

**Phase 1 subtotal: 50 SP**

---

## Phase 2: Scoring Engine + API (Epics #2, #5)

| Issue | Title                                | PR   | Author | +/-     | Files | SP  | Rationale                    |
| ----- | ------------------------------------ | ---- | ------ | ------- | ----- | --- | ---------------------------- |
| #23   | Signal taxonomy + weights            | #91  | arun   | +433/-0 | 4     | 5   | Core domain model            |
| #24   | Signal extraction per case           | #92  | arun   | +531/-0 | 2     | 5   | Complex business logic       |
| #25   | Risk + legitimacy score computation  | #93  | arun   | +248/-0 | 2     | 5   | Scoring algorithm            |
| #26   | On-the-fly scoring for new claims    | #96  | arun   | +396/-0 | 3     | 5   | Real-time scoring endpoint   |
| #27   | Scoring engine tests (>90% coverage) | —    | arun   | —       | —     | 3   | Test suite                   |
| #35   | FastAPI app factory + middleware     | —    | arun   | —       | —     | 3   | App scaffold                 |
| #36   | /api/providers endpoints             | #88  | arun   | +433/-0 | 4     | 5   | List + detail endpoints      |
| #37   | /api/claims with pagination          | #97  | arun   | +336/-0 | 3     | 5   | Paginated endpoint           |
| #38   | /api/score endpoint                  | —    | arun   | —       | —     | 3   | Scoring endpoint             |
| #39   | /api/signals + /api/peers            | #99  | arun   | +421/-0 | 3     | 5   | Two related endpoints        |
| #40   | Pydantic schemas for all models      | —    | arun   | —       | —     | 5   | 60+ field schemas            |
| #62   | Fairness analysis endpoint           | #98  | arun   | +405/-0 | 3     | 5   | Statistical analysis         |
| #101  | GET /api/dashboard                   | #107 | arun   | +391/-0 | 3     | 5   | Aggregate stats              |
| #102  | GET /api/dashboard/heatmap           | #107 | arun   | —       | —     | 3   | State-level risk map         |
| #183  | 14th signal: concentration_outlier   | #225 | arun   | +93/-1  | 4     | 3   | New signal + HHI calc        |
| #185  | Fix risk threshold mismatch          | #213 | arun   | +38/-5  | 3     | 2   | Bug fix, threshold alignment |
| #187  | GET /api/validation endpoint         | #214 | arun   | +344/-0 | 4     | 5   | Detection rate stats         |
| #188  | Fix peer z-scores in score/simulate  | #219 | arun   | +15/-5  | 2     | 2   | Bug fix                      |

**Phase 2 subtotal: 74 SP**

---

## Phase 3: AI Reasoning Layer (Epic #4)

| Issue | Title                                    | PR   | Author  | +/-       | Files | SP  | Rationale               |
| ----- | ---------------------------------------- | ---- | ------- | --------- | ----- | --- | ----------------------- |
| #28   | Bedrock client wrapper                   | #158 | arun    | +499/-0   | 5     | 5   | AWS integration         |
| #29   | Schema prompt + few-shot                 | #158 | arun    | —         | —     | 3   | Prompt engineering      |
| #30   | Text-to-SQL with validation              | #159 | arun    | +276/-0   | 2     | 5   | NL→SQL engine           |
| #31   | Risk narrative generator                 | #160 | arun    | +227/-0   | 4     | 5   | AI narrative pipeline   |
| #32   | Chat endpoint + conversation history     | #161 | arun    | +215/-26  | 4     | 5   | Stateful chat API       |
| #33   | Chart spec generator                     | #237 | arun    | +478/-9   | 7     | 5   | AI → Recharts config    |
| #34   | Test AI with 20+ questions               | #238 | arun    | +182/-0   | 1     | 3   | Integration test suite  |
| #164  | Retrospective validation (91% detection) | #173 | arun    | +1132/-26 | 14    | 13  | Major validation study  |
| #165  | Isolation forest anomaly model           | #177 | arun    | +775/-0   | 5     | 8   | ML model training       |
| #166  | Network risk signal (graph)              | #175 | arun    | +270/-6   | 6     | 5   | Graph + SQL integration |
| #167  | Harden text-to-SQL (injection)           | #171 | arun    | +90/-2    | 2     | 3   | Security hardening      |
| #168  | Fairness revocation-blind mode           | #178 | arun    | +873/-7   | 7     | 8   | Complex analysis mode   |
| #182  | Wire isolation forest into API           | #223 | arun    | +445/-85  | 15    | 8   | Model integration       |
| #189  | Chat multi-row LLM synthesis             | #226 | arun    | +113/-1   | 2     | 3   | Prompt improvement      |
| #190  | Enrich /score narrative context          | #230 | copilot | +318/-83  | 13    | 5   | Narrative enhancement   |
| #203  | Fix ChatMessage.role validation          | #216 | copilot | +19/-1    | 2     | 1   | Type fix                |

**Phase 3 subtotal: 85 SP**

---

## Phase 4: Frontend UI (Epics #6, #7, #14)

| Issue | Title                                 | PR   | Author  | +/-       | Files | SP  | Rationale                |
| ----- | ------------------------------------- | ---- | ------- | --------- | ----- | --- | ------------------------ |
| #41   | Scaffold Next.js + shadcn/ui          | #130 | arun    | +11663/-0 | 38    | 8   | Full framework scaffold  |
| #42   | Claims data table                     | #134 | arun    | +251/-3   | 4     | 3   | Table component          |
| #43   | Provider detail panel + signals       | #133 | arun    | +370/-0   | 3     | 5   | Detail page              |
| #44   | Risk gauge component                  | #139 | arun    | +74/-13   | 3     | 2   | Single component         |
| #45   | Peer comparison chart                 | #135 | arun    | +135/-0   | 2     | 3   | Recharts bar chart       |
| #46   | Scan button flow                      | #138 | arun    | +152/-0   | 2     | 3   | Scoring integration      |
| #47   | Chat sidebar shell                    | #163 | arun    | +236/-2   | 4     | 3   | Slide panel UI           |
| #48   | Message list + text input             | —    | arun    | —         | —     | 2   | Chat components          |
| #49   | Integrate chat with /api/chat         | —    | arun    | —         | —     | 3   | API integration          |
| #50   | Inline chart renderer for AI          | #237 | arun    | —         | —     | 5   | Dynamic chart rendering  |
| #51   | Suggested starter questions           | —    | arun    | —         | —     | 1   | Static UI                |
| #59   | Overview dashboard                    | #131 | arun    | +269/-111 | 3     | 5   | Landing page with KPIs   |
| #60   | Risk heatmap (geographic)             | #136 | arun    | +155/-6   | 1     | 5   | Interactive state map    |
| #63   | Fairness dashboard                    | #137 | arun    | +272/-5   | 3     | 5   | Charts + parity metrics  |
| #64   | Provider search with autocomplete     | #132 | arun    | +236/-11  | 2     | 3   | Search with debounce     |
| #66   | Evidence graph viz                    | #140 | arun    | +518/-3   | 5     | 5   | Force-directed graph     |
| #145  | Claim submission form                 | #155 | arun    | +794/-51  | 11    | 8   | Multi-step form          |
| #146  | Scoring result display                | #156 | arun    | +165/-59  | 1     | 3   | Result component         |
| #147  | Claims inbox (prioritized queue)      | —    | arun    | —         | —     | 5   | Queue page               |
| #149  | Investigation workflow (case actions) | #172 | arun    | +711/-26  | 10    | 8   | Full workflow            |
| #150  | Unified investigation view            | #243 | copilot | +665/-111 | 7     | 8   | Provider deep-dive       |
| #151  | Activity log / audit trail            | —    | arun    | —         | —     | 5   | Case timeline            |
| #192  | Investigation inbox page              | #241 | copilot | +388/-1   | 2     | 5   | Queue frontend           |
| #193  | Fix heatmap state filter              | #240 | copilot | +64/-12   | 1     | 2   | Bug fix                  |
| #194  | Provider filter controls              | #242 | copilot | +159/-37  | 1     | 3   | Filter dropdowns         |
| #232  | Chat data tables + stat cards         | #233 | arun    | +188/-24  | 2     | 3   | Chat result rendering    |
| #244  | Spider/radar chart                    | #245 | arun    | +304/-36  | 8     | 5   | Risk profile chart       |
| #251  | Collapsible sidebar (mobile)          | #257 | copilot | +246/-54  | 4     | 5   | Responsive drawer + a11y |
| #252  | Table horizontal scroll               | #260 | copilot | +4/-4     | 4     | 1   | CSS min-width fix        |
| #253  | Unicode KPI fix                       | #263 | copilot | +1/-1     | 1     | 1   | One-char fix             |
| #254  | Responsive provider header            | #261 | copilot | +6/-6     | 2     | 2   | CSS flex-wrap            |
| #255  | Fairness chart label clipping         | #264 | copilot | +7/-1     | 1     | 2   | Truncate + margin fix    |
| #256  | Responsive investigate buttons        | #262 | copilot | +89/-29   | 2     | 3   | Mobile overflow menu     |

**Phase 4 subtotal: 138 SP**

---

## Phase 5: Ship / Docs / Infra (Epics #9, #10, #13)

| Issue | Title                              | PR        | Author  | +/-       | Files | SP  | Rationale           |
| ----- | ---------------------------------- | --------- | ------- | --------- | ----- | --- | ------------------- |
| #52   | Kustomize manifests                | —         | arun    | —         | —     | 5   | K8s overlays        |
| #53   | ArgoCD app manifest + CD           | —         | arun    | —         | —     | 3   | GitOps setup        |
| #54   | Architecture diagram               | —         | arun    | —         | —     | 2   | Diagram generation  |
| #55   | Risk-scoring methodology doc       | #100      | arun    | +312/-0   | 2     | 3   | Technical doc       |
| #56   | Responsible AI considerations      | #100      | arun    | —         | —     | 3   | Ethics doc          |
| #57   | Path to CMS Pilot briefing         | #108      | arun    | +92/-0    | 1     | 2   | One-page brief      |
| #58   | AI tool + OSS disclosure + demo    | —         | arun    | —         | —     | 3   | Compliance doc      |
| #70   | Demo script (5-7 min)              | #179      | arun    | +1240/-26 | 15    | 8   | Full demo script    |
| #90   | Sprint plan for parallel dev       | #89       | arun    | +109/-0   | 1     | 2   | Planning doc        |
| #106  | AI tool usage disclosure           | —         | arun    | —         | —     | 2   | Compliance doc      |
| #113  | Create ECR repository              | —         | arun    | —         | —     | 2   | Terraform resource  |
| #114  | K8s manifests (PG, Neo4j, API)     | #128      | arun    | +374/-0   | 6     | 8   | Full K8s stack      |
| #115  | ArgoCD app + precise-manifests     | #129      | arun    | +35/-5    | 3     | 3   | Cross-repo GitOps   |
| #116  | CI: build + push to ECR            | #127      | arun    | +48/-0    | 1     | 2   | Deploy workflow     |
| #117  | Seed data on EKS                   | —         | arun    | —         | —     | 5   | Data migration      |
| #118  | Terraform state backend (S3 + DDB) | —         | arun    | —         | —     | 2   | Infra setup         |
| #119  | IAM service account for CI/CD      | —         | arun    | —         | —     | 2   | IAM + secrets       |
| #120  | GitHub repo secrets for CI/CD      | —         | arun    | —         | —     | 1   | Config              |
| #121  | Terraform ECR module               | #123      | arun    | +255/-0   | 9     | 3   | TF module           |
| #122  | Scaffold Terraform project         | #123      | arun    | —         | —     | 3   | TF structure        |
| #124  | CI: Terraform plan/apply           | #125      | arun    | +178/-10  | 6     | 3   | TF CI workflow      |
| #143  | Claims simulation API schema       | #153      | arun    | +87/-0    | 2     | 2   | Schema design       |
| #144  | POST /api/claims/simulate          | #154      | arun    | +305/-0   | 5     | 5   | Real-time scoring   |
| #148  | User personas + journeys doc       | #152      | arun    | +258/-0   | 1     | 3   | UX documentation    |
| #169  | k6 load test script                | #174      | arun    | +128/-0   | 2     | 3   | Perf test           |
| #170  | Fix AI framing in docs             | #176      | arun    | +28/-17   | 2     | 1   | Doc fix             |
| #181  | AI + OSS disclosure doc            | —         | arun    | —         | —     | 2   | Compliance          |
| #184  | Fix signal taxonomy diagram        | #215      | arun    | +18/-17   | 1     | 1   | Diagram fix         |
| #186  | Update responsible AI doc          | #205      | copilot | +51/-5    | 1     | 1   | Doc update          |
| #191  | Isolation forest model card        | #227      | arun    | +86/-77   | 1     | 2   | ML model doc        |
| #195  | Judge Resources in README          | #204      | copilot | +205/-1   | 4     | 2   | README section      |
| #196  | Fix version inconsistencies        | #200      | copilot | +6/-6     | 4     | 1   | Doc fix             |
| #202  | Final EKS deployment sweep         | —         | arun    | —         | —     | 5   | Deploy verification |
| #234  | Chat timeout + Docker fix          | #235+#236 | arun    | +9/-3     | 5     | 2   | Deploy bug fix      |

**Phase 5 subtotal: 96 SP**

---

## Standalone / Cross-cutting

| Issue | Title                    | PR  | Author | +/- | Files | SP  | Rationale                     |
| ----- | ------------------------ | --- | ------ | --- | ----- | --- | ----------------------------- |
| #61   | Time-series trend charts | —   | arun   | —   | —     | 5   | Chart component (descoped)    |
| #65   | Streaming chat (SSE)     | —   | arun   | —   | —     | 5   | SSE implementation (descoped) |

**Cross-cutting subtotal: 10 SP**

---

## Summary

| Phase                        | SP      | Issues  |
| ---------------------------- | ------- | ------- |
| Phase 0: Spine / CI/CD       | 27      | 13      |
| Phase 1: Data Foundation     | 50      | 12      |
| Phase 2: Scoring + API       | 74      | 18      |
| Phase 3: AI Layer            | 85      | 16      |
| Phase 4: Frontend UI         | 138     | 33      |
| Phase 5: Ship / Infra / Docs | 96      | 34      |
| Cross-cutting                | 10      | 2       |
| **TOTAL**                    | **480** | **128** |

## Contributor Breakdown (by merged PRs)

| Contributor            | PRs Merged | Story Points | Lines Added  |
| ---------------------- | ---------- | ------------ | ------------ |
| arunsanna (human)      | ~75        | ~430         | ~35,000+     |
| copilot-swe-agent (AI) | ~15        | ~50          | ~3,500+      |
| **Total**              | **~90**    | **480**      | **~38,500+** |

## Open Issues (4 remaining, unpointed)

| Issue | Title                                | Status             |
| ----- | ------------------------------------ | ------------------ |
| #9    | Epic 9: Documentation & Deliverables | OPEN (epic, no SP) |
| #69   | Set up judge access to private repo  | OPEN               |
| #197  | Epic 13: Competition Hardening       | OPEN (epic, no SP) |
| #201  | Demo rehearsal with live EKS         | OPEN               |
