# Plan 01 — Dependency upgrades & vulnerability remediation

- **Wave:** 0 (blocker — run alone, everything else builds/tests against the result)
- **Depends on:** nothing
- **Priority:** P0 — GitHub reports 152 vulnerabilities (2 critical) on `master`

## Objective

Upgrade all backend Python pins and frontend npm dependencies to current,
non-vulnerable versions without breaking the 397-test suite or the docker build.

## Context

`backend/requirements.txt` pins 2023-era versions:
`fastapi==0.104.1`, `uvicorn==0.24.0`, `sqlalchemy==2.0.23`,
`pydantic==2.5.0`, `PyPDF2==3.0.1` (EOL, superseded by `pypdf`),
`python-multipart==0.0.6` (known CVE), `pytest==7.4.4`,
`pytest-asyncio==0.23.3`, `httpx==0.27.2`, `litellm>=1.40.0` (unpinned floor).
Frontend uses `^` ranges but has not had an `npm audit` pass.

## Tasks

1. Upgrade `backend/requirements.txt` (verify each against its changelog for
   breaking changes):
   - `fastapi` → latest 0.115.x
   - `uvicorn[standard]` → latest 0.32+
   - `sqlalchemy` → latest 2.0.x
   - `pydantic` → latest 2.10.x (check `model_construct` / `model_validate`
     usage still behaves the same)
   - **Replace `PyPDF2` with `pypdf`** (drop-in successor; update
     `services/document_service.py` import `from pypdf import PdfReader`)
   - `python-multipart` → latest (fixes CVE-2024-24762 class issues)
   - `python-dotenv`, `alembic`, `psycopg2-binary` → latest
   - `litellm` → pin an exact recent version (replace `>=1.40.0` floor)
   - `pytest`, `pytest-asyncio`, `httpx` → latest compatible majors
     (pytest-asyncio 0.24+ changed async-test defaults — check
     `pytest.ini` for `asyncio_mode` if any async tests exist)
2. Regenerate the lockfile-equivalent: record `pip freeze` output in the PR
   description (no requirements.lock file exists; do not invent one unless
   the team wants one).
3. Frontend: run `npm audit` inside the node container
   (`docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine
sh -c "npm ci && npm audit"`), then `npm update` + targeted `npm install
<pkg>@latest` for vulnerable packages (axios, react-router-dom, etc.).
   Commit the updated `package.json` **and** `package-lock.json` together.
4. Rebuild and verify (see below). Fix any deprecation warnings that fail
   tests (e.g. FastAPI `regex=` → `pattern=` in `Query(...)` — check
   `routes/documents.py` and `routes/questions.py`).

## Files owned

- `backend/requirements.txt`
- `backend/services/document_service.py` (PyPDF2 → pypdf import)
- `backend/routes/*.py` (only if FastAPI deprecations require it)
- `frontend/package.json`, `frontend/package-lock.json`

## Verification

```bash
cd backend && python3 -m pip install -r requirements.txt   # clean install
python3 -m ruff check backend/ && python3 -m ruff format --check backend/
cd backend && python3 -m pytest tests/ --cov=. --cov-report=term   # 397 pass, ≥90%
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
docker compose -f docker-compose.yml build --no-cache
docker compose -f docker-compose.yml up -d
curl -fsS http://localhost:8001/health
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  sh -c "npm ci --no-fund --no-audit && npm audit && npm run build"
```

## Done criteria

- `pip install` clean, all 397 tests pass, coverage ≥90%, docker stack healthy,
  `npm audit` reports 0 vulnerabilities (or only unfixable ones with a written
  note), frontend build succeeds.

## Risks

- pydantic/fastapi majors can change validation behavior — watch the 422-vs-400
  tests in `test_questions_api.py`.
- pytest-asyncio 0.24+ defaults `asyncio_mode=strict`; if async tests exist,
  add `asyncio_mode = "auto"` to `backend/pytest.ini`.
- Do **not** upgrade Python base images (`python:3.11-slim`, `node:20-alpine`)
  in the same change — keep the diff reviewable.
