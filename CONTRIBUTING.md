# Contributing

Thanks for contributing to the LLM-Based Interview Prep
Platform! This guide covers the development workflow and
the CI gates every change must pass.

## Development setup

See the [README](README.md) for the full stack setup.
In short:

```bash
# Production-like stack (Postgres + FastAPI + Nginx)
docker compose -f docker-compose.yml up --build

# Dev stack with hot reload (Vite HMR + uvicorn --reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
#   Frontend (Vite dev server): http://localhost:5173
#   Backend (uvicorn --reload): http://localhost:8001
```

## CI gates

Every pull request must pass the following GitHub Actions
jobs (`.github/workflows/ci.yml` and
`.github/workflows/pre-commit.yml`):

| Job                 | What it checks                                                          |
| ------------------- | ----------------------------------------------------------------------- |
| `lint-backend`      | `ruff check` and `ruff format --check` on `backend/`                    |
| `lint-frontend`     | `prettier --check` on `src/**` and a full `tsc + vite build`            |
| `test`              | `pytest` with a coverage gate: total coverage must be `>= 90%`          |
| `docker`            | `docker compose build` succeeds for both images                         |
| `dependency-review` | Flags PRs that introduce vulnerable or license-conflicting dependencies |
| `pre-commit`        | Runs the hooks from `.pre-commit-config.yaml` (ruff, prettier, hygiene) |

### Running the gates locally

```bash
# Backend lint
cd backend && python -m pip install ruff==0.6.9
ruff check . && ruff format --check .

# Backend tests + coverage (enforces the >= 90% gate)
python -m pip install -r requirements.txt
./scripts/check_coverage.sh

# To run tests without the coverage gate
python -m pytest tests/

# Frontend lint + build
cd frontend && npm ci
npx prettier --check "src/**/*.{ts,tsx,css,js}" index.html
npm run build

# Pre-commit hooks (all files)
pip install pre-commit && pre-commit run --all-files
```

> **Note:** the coverage gate is driven by `scripts/check_coverage.sh`
> (`coverage run` + `coverage report`), not by `pytest --cov-fail-under`
> flags in `addopts`. With a directory argument such as `pytest tests/`,
> `pytest-cov` loses import tracking in this environment and reports `0%`
> for every module, so an addopts-based gate fails no matter how well the
> tests cover the code. The threshold lives in
> `backend/.coveragerc` under `[report] fail_under`.

### Test suite layout

`backend/pytest.ini` is an INI file, so its header must be `[pytest]` and
its values must be bare — `testpaths = tests`, not `testpaths = ["tests"]`.
Bracketed TOML values are read literally by pytest, which silently collects
zero tests.

## Database migrations

Schema changes are managed with Alembic — see
[Database Migrations](README.md#database-migrations-alembic)
in the README. Never edit `db/init.sql`; add a migration
instead.

## Pinning GitHub Actions

The workflows reference actions by major-version tag
(e.g. `actions/checkout@v4`). For production repositories,
pin each `uses:` to the full immutable commit SHA to
protect against tag-moving attacks:

```yaml
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

To resolve a tag to its commit SHA:

```bash
git ls-remote https://github.com/actions/checkout.git \
  "refs/tags/v4.2.2^{}"
```

Record the SHA in a trailing comment (as shown above) so
the pin is auditable.

## Commit messages

Write clear, descriptive commit messages. Reference the
plan/issue a change addresses when relevant.
