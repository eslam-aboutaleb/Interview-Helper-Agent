# Plan 02 — CI/CD pipeline (GitHub Actions)

- **Wave:** 1 (after Plan 01)
- **Depends on:** 01 (CI must run against the upgraded dependency set)
- **Priority:** P0 — pre-commit exists locally but nothing enforces it in the repo

## Objective

Add GitHub Actions workflows that run the same checks the pre-commit config
enforces, plus tests with a coverage gate and a docker build, on every push
and PR.

## Context

- `.pre-commit-config.yaml` exists (ruff, ruff-format, prettier, hooks) but
  there is no `.github/` directory at all.
- Backend tests: `cd backend && python3 -m pytest tests/ --cov=.`
- Prettier must run in a node container locally, but GitHub runners have node.
- Dependabot already opened 152 alerts; CI should include the
  dependency-review action so vulnerable PRs fail.

## Tasks

1. Create `.github/workflows/ci.yml` with jobs:
   - **lint-backend** (ubuntu-latest, python 3.11): `pip install ruff==<pinned>`,
     `ruff check backend/`, `ruff format --check backend/`
   - **lint-frontend** (ubuntu-latest, node 20): `npm ci` in `frontend/`,
     `npx prettier --check` on the same globs as `.pre-commit-config.yaml`,
     `npm run build` (tsc + vite)
   - **test** (python 3.11): `pip install -r backend/requirements.txt`,
     `pytest --cov=. --cov-report=xml --cov-fail-under=90` in `backend/`,
     upload coverage artifact
   - **docker** (ubuntu-latest): `docker compose -f docker-compose.yml build`
     (proves both images still build)
   - **dependency-review** on PRs: `actions/dependency-review-action@v4`
2. Create `.github/workflows/pre-commit.yml` using
   `pre-commit/action@v3.0.1` so the local hook set runs in CI too (catches
   trailing whitespace, end-of-file, YAML/JSON validity).
3. Pin all action versions to full SHAs where feasible (security best practice);
   at minimum use major-tag pins and record the SHA in a comment.
4. Add a `CONTRIBUTING.md` section (or note in README) describing the CI gates.

## Files owned

- `.github/workflows/ci.yml` (new)
- `.github/workflows/pre-commit.yml` (new)
- `README.md` or `CONTRIBUTING.md` (CI documentation)

## Verification

- `git push` triggers the workflow; check the Actions tab shows all jobs green.
- Locally simulate: run the exact commands from each job step.
- Negative test: push a branch with a deliberate ruff error and confirm CI fails
  (then revert).

## Done criteria

- All workflows green on `master`; a deliberately broken branch fails CI;
  coverage gate rejects <90%.

## Risks

- `docker compose build` in CI needs the build context to include only
  necessary files — verify `.dockerignore` files exist (frontend has one;
  check backend has one too, add if missing).
- Coverage gate at 90% must match Plan 05's outcome (97% today — safe).
