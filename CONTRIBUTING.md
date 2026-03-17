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

These checks run automatically on every PR:

| Workflow | Jobs                                                     | Blocks Merge? |
| -------- | -------------------------------------------------------- | ------------- |
| CI       | Lint (ruff), Type check (mypy), Test (pytest + coverage) | Yes           |
| Secrets  | gitleaks scan                                            | Yes           |
| Security | pip-audit (dependency CVEs), bandit (SAST)               | Yes           |

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
- Update the parent epic checklist if applicable
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
python -m venv .venv
source .venv/bin/activate  # or: . .venv/bin/activate.fish
pip install -e ".[dev]"
```

## Project Structure

```
src/
  api/          FastAPI app, routes, schemas
  data/         Data loading, CSV generation
  pipeline/     Feature engineering (Polars)
  models/       ML models (future)
  explainability/ SHAP explanations (future)
tests/          pytest test suite
.github/
  workflows/    CI/CD pipelines
db/             Database schema (init.sql)
```
