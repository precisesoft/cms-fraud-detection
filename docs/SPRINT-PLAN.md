# Sprint Plan — Parallel Development

## Team

- **Arun** — Lead developer. Owns core scoring engine, architecture decisions, and code review.
- **Bibek** — Supporting developer. Owns API endpoints (following established patterns), frontend scaffold, and infrastructure.

## How We Work

- One issue per person at a time. Label it `in-progress` when you start.
- Follow CONTRIBUTING.md exactly — branch, implement, local CI, PR, review, merge.
- Arun reviews Bibek's PRs. Bibek reviews Arun's PRs when possible.
- Don't start a dependent issue until its blocker is merged to main.

---

## Arun's Issues (Scoring Engine + Core Backend)

These are sequential — do them in this order:

1. **#23** — Define signal taxonomy and weights (`src/scoring/taxonomy.py`)
2. **#24** — Implement signal extraction per case (depends on #23)
3. **#25** — Implement risk + legitimacy score computation (depends on #24)
4. **#26** — Implement on-the-fly scoring for new claims (depends on #25)
5. **#27** — Write scoring engine tests, >90% coverage (depends on #25)
6. **#38** — `/api/score` endpoint (depends on #25, exposes the engine via API)
7. **#62** — Fairness analysis across geography and specialty (depends on scoring)

Why Arun: This is the core IP of the project. The signal taxonomy and scoring weights define how fraud detection works. These decisions need the lead developer.

---

## Bibek's Issues (API + Infra + Frontend)

These can start immediately — no dependency on Arun's scoring work:

### Start now (parallel with Arun)

1. **#37** — `/api/claims` endpoint with pagination and filtering
   - Same pattern as #36 (providers). Look at `src/api/routes/providers.py` as the template.
   - Queries `provider_service_cases` table instead of `provider_features`.
   - Filters: case_label, state, provider_type, risk_score range.

2. **#39** — `/api/signals/{npi}` and `/api/peers/{npi}`
   - Two more endpoints following the same router pattern.
   - Can start once #37 is merged (to avoid merge conflicts in app.py router registration).

3. **#13** — Multi-stage Dockerfile (backend only for now, frontend blocked on #41)
   - Python 3.12 slim base, multi-stage build.
   - Independent of all API work.

### After #13 is done

4. **#52** — Kustomize manifests (base + dev + prod overlays)
5. **#53** — ArgoCD Application manifest + CD workflow

### When ready for frontend

6. **#41** — Scaffold Next.js 15 + shadcn/ui + Tailwind
   - This unblocks all 14 frontend issues.
   - Can start any time — independent of backend.

---

## Dependency Map

```
Arun's chain (sequential):
  #23 → #24 → #25 → #26
                 ↘ #27 (tests)
                 ↘ #38 (/api/score)
                       ↘ #62 (fairness)

Bibek's chain:
  #37 (/api/claims) → #39 (/api/signals + /api/peers)
  #13 (Dockerfile) → #52 (k8s) → #53 (ArgoCD)
  #41 (frontend scaffold) → #42-#66 (all UI issues)

No cross-dependencies between Arun and Bibek until:
  - #38 needs scoring engine (#25) done by Arun
  - Frontend integration (#46) needs /api/score from Arun
```

---

## What Can Run in Parallel Right Now

Arun starts #23 (signal taxonomy). Bibek starts #37 (claims endpoint). No overlap, no blockers, different files entirely.

---

## Code Review Rules

- Every PR gets reviewed by the other person before merge.
- Reviewer checks: CI green, follows CONTRIBUTING.md, no scope creep, tests included.
- If the other person is unavailable, self-review with BASSPC checklist is acceptable.

---

## Documentation (assign when bandwidth allows)

These are independent of all code work:

- **#55** — Risk-scoring methodology document (Arun — needs scoring domain knowledge)
- **#56** — Responsible AI considerations (Arun)
- **#57** — Path to CMS Pilot briefing (Arun)
- **#58** — AI tool + OSS disclosure (either)
- **#70** — Demo script and rehearsal (both, later)
- **#69** — Set up judge access to repo (Arun — repo admin)
