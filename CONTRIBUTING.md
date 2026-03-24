# Contributing to CMS Fraud Detection

## Development Workflow (SDLC)

Every change follows this process. No exceptions.

```
Issue → Branch → Implement → Local CI → Commit → Push → PR → CI Green → Review → Merge → Cleanup
```

### 1. Pick an Issue

- Choose from the [issue backlog](https://github.com/precisesoft/cms-fraud-detection/issues)
- Label it `in-progress`
- One issue at a time per developer

### 2. Create a Branch

```bash
git checkout main && git pull
git checkout -b <type>/<issue-number>-<short-description>
```

Branch naming:
| Type | When |
|------|------|
| `feat/` | New feature or capability |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `ci/` | CI/CD changes |
| `refactor/` | Code restructure, no behavior change |
| `test/` | Test additions or fixes |
| `chore/` | Dependency updates, config changes |

Examples: `feat/36-providers-endpoint`, `fix/42-null-score`, `ci/72-dependabot`

### 3. Implement

- Work on your branch, never on `main`
- Keep changes focused on the issue scope

### 4. Verify Locally Before Pushing

Run the exact CI commands before your first push:

```bash
# Lint + format
ruff check src/ tests/
ruff format --check src/ tests/

# Type check
mypy src/

# Tests + coverage
pytest --cov=src --cov-report=term -q

# Security (optional but recommended)
pip-audit --skip-editable
bandit -r src/ -c pyproject.toml
```

### 5. Commit

Use conventional commits. Every commit references the issue.

```
type(scope): description (#N)
```

| Type       | Description   |
| ---------- | ------------- |
| `feat`     | New feature   |
| `fix`      | Bug fix       |
| `docs`     | Documentation |
| `ci`       | CI/CD         |
| `refactor` | Restructure   |
| `test`     | Tests         |
| `chore`    | Maintenance   |

Examples:

```
feat(api): add providers endpoint (#36)
fix(ci): skip editable package in pip-audit (#71)
docs(sdlc): add CONTRIBUTING.md (#81)
```

Rules:

- Present tense, lowercase, no period
- Under 72 characters
- Explain "why" not "what" in the body (if needed)

### 6. Push and Create PR

```bash
git push -u origin <branch-name>
gh pr create --title "type(scope): description" --body "Closes #N ..."
```

PR body must include:

- `Closes #N` (auto-closes the issue on merge)
- Summary of changes
- Test plan (what was verified)

### 7. CI Must Pass

All jobs run in a single unified workflow (`pipeline.yml`) on every PR:

| Stage            | Jobs                                               | Blocks Merge? |
| ---------------- | -------------------------------------------------- | ------------- |
| Gate             | Conventional commit PR title check                 | Yes           |
| Security         | gitleaks + bandit + pip-audit + npm audit          | Yes           |
| Quality Backend  | ruff lint + mypy + pytest (80% coverage threshold) | Yes           |
| Quality Frontend | eslint + tsc + vitest (80% lines) + vite build     | Yes           |
| Build            | Docker images (amd64) + CycloneDX SBOMs            | Yes           |
| Scan             | Trivy on both images (informational)               | No            |

On merge to main, additional Release (push to ECR) and Deploy (update manifests) jobs run.

All checks must be green before merge.

### 8. Review

- Self-review your own PR before requesting review
- At least 1 approval required (when branch protection is active)
- Address all review comments

### 9. Merge

- **Squash merge** only (keeps main history clean)
- Delete the branch after merge

### 10. Cleanup

After merge:

- Verify the issue was auto-closed
- Comment on the issue with the PR number (e.g., `Resolved in PR #N`)
- Update the parent epic checklist: mark issue as CLOSED with PR number
- Remove `in-progress` label from the issue
- `git checkout main && git pull`

## What NOT to Do

- Never push directly to `main`
- Never force push to `main`
- Never merge without CI passing
- Never skip the PR process for "quick fixes"
- Never batch multiple issues into one PR
- Never merge your own PR without at least self-review

## Local Setup

```bash
# Backend
python -m venv .venv
source .venv/bin/activate  # or: . .venv/bin/activate.fish
pip install -e ".[dev]"

# Frontend
cd frontend && npm install
```

### Verify locally (backend + frontend)

```bash
# Backend
ruff check src/ tests/ && ruff format --check src/ tests/
mypy src/
pytest --cov=src --cov-report=term -q

# Frontend
cd frontend
npm run lint
npx tsc --noEmit
npm test
npm run build
```

## Project Structure

```
src/
  api/            FastAPI app, routes (14 modules), schemas
  scoring/        Signal taxonomy, extraction, score computation
  ai/             AWS Bedrock: text-to-SQL, narratives, chat
  models/         Isolation Forest anomaly detection
  validation/     Retrospective validation
  data/           Data loading, Neo4j projection
  pipeline/       Feature engineering (Polars)
frontend/
  src/pages/      React page components (Dashboard, Simulate, ...)
  src/components/ Shared components (Layout, AssistantDrawer, ...)
  src/lib/        API client, helpers
  src/contexts/   React context (AuthContext)
tests/            Backend pytest suite (30+ test files)
.github/
  workflows/      pipeline.yml (unified CI/CD) + terraform.yml
  agents/         Copilot agent personas
db/               Database schema (init.sql)
k8s/              Kubernetes manifests (EKS)
terraform/        AWS infrastructure (ECR, IAM)
```
