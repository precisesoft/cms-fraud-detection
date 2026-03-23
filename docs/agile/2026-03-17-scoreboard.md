# Sprint Scoreboard -- 2026-03-17

**Target**: CMS AI Hackathon demo -- March 27, 2026 (10 days remaining)

## Summary

Day 3. Data foundation complete -- all provider data loaded into PostgreSQL (10,282 providers, 13,225 cases). CI/CD pipeline fully stood up with 7 workflows. Scoring engine signal taxonomy defined and first endpoint live. Added 8 new CI/CD issues as security scanning and linting needs became clear.

## Today's Activity

| Metric         | Value |
| -------------- | ----- |
| Issues created | 8     |
| Issues closed  | 12    |
| SP delivered   | 28    |
| PRs merged     | 13    |

## What Shipped

- **PR #77** -- GitHub Actions CI workflow: ruff lint + pytest (#11)
- **PR #78** -- Gitleaks secrets scanning (#73)
- **PR #79** -- Security scanning: pip-audit + bandit (#71)
- **PR #80** -- mypy type checking gate (#74)
- **PR #82** -- CONTRIBUTING.md + CLAUDE.md with SDLC process (#81)
- **PR #83** -- Dependabot configuration (#72)
- **PR #84** -- Branch protection rules + PR template (#14)
- **PR #85** -- Conventional commit lint (#75)
- **PR #86** -- SBOM generation with CycloneDX (#76)
- **PR #87** -- Post-merge cleanup steps in docs
- **PR #88** -- /api/providers and /api/providers/{npi} endpoints (#36)
- **PR #89** -- Sprint plan for parallel development (#90)
- **PR #91** -- Signal taxonomy and weights (#23)

## Issues Closed

#11, #14, #23, #36, #71, #72, #73, #74, #75, #76, #81, #90

## Issues Created

#71 - #76, #81, #90 (CI/CD and process issues)

## Cumulative

| Metric       | Value |
| ------------ | ----- |
| Total issues | 78    |
| Closed       | 23    |
| SP delivered | 68    |
| PRs merged   | 13    |
| % Done       | 29%   |
