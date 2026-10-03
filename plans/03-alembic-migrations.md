# Plan 03 — Alembic migrations

- **Wave:** 1 (after Plan 01)
- **Depends on:** 01
- **Priority:** P1 — `alembic.ini` exists but there is no `alembic/` directory;
  schema changes currently rely on `Base.metadata.create_all()` which cannot
  alter existing tables

## Objective

Set up a real Alembic migration environment, generate the initial migration from
the current models, and wire it into the app and docker workflow — while
keeping `create_all()` as a dev fallback.

## Context

- `backend/alembic.ini` exists with a placeholder
  `sqlalchemy.url = driver://user:pass@localhost/dbname`.
- `backend/database.py` builds the engine from `DATABASE_URL` env var.
- `backend/main.py:ensure_db_initialized()` calls `Base.metadata.create_all()`.
- Models: `backend/models.py` (10 tables).

## Tasks

1. Scaffold `backend/alembic/`:
   - `env.py` — import `database.engine` and `models.Base.metadata`;
     `target_metadata = Base.metadata`; read URL from the existing engine
     (ignore `sqlalchemy.url` in alembic.ini); enable `compare_type=True`.
   - `script.py.mako` (standard template).
   - `versions/` (empty, with `.gitkeep`).
2. Generate the initial migration:
   `cd backend && alembic revision --autogenerate -m "initial schema"` and
   review that all 10 tables + columns + constraints are present.
3. Update `alembic.ini`: remove the placeholder URL (env.py is authoritative),
   set `script_location = alembic`.
4. Keep `ensure_db_initialized()` but make it log that it is a fallback;
   document in `README.md` the migration workflow:
   `alembic revision --autogenerate -m "..."` → `alembic upgrade head`.
5. Add a `db` service step to the docker workflow: after the stack is up,
   `docker compose exec backend /app/venv/bin/alembic upgrade head` must be a
   no-op ("no pending upgrades") against the already-created schema.
6. Test a real migration path: spin up a **fresh** database (new volume name),
   run `alembic upgrade head` only (no create_all), verify all tables exist
   via `psql '\dt'`, then run the test suite against it.

## Files owned

- `backend/alembic/env.py`, `backend/alembic/script.py.mako` (new)
- `backend/alembic/versions/<hash>_initial_schema.py` (new, generated)
- `backend/alembic.ini`
- `backend/main.py` (fallback log message only)
- `README.md` (migration workflow docs)

## Verification

```bash
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
# fresh-volume migration test
docker compose -f docker-compose.yml down -v
docker compose -f docker-compose.yml up -d db
docker compose -f docker-compose.yml exec -T backend \
  /app/venv/bin/alembic upgrade head
docker compose -f docker-compose.yml exec -T db \
  psql -U postgres -d interview_prep -c '\dt'   # 10 tables
docker compose -f docker-compose.yml up -d
curl -fsS http://localhost:8001/health
```

## Done criteria

- `alembic upgrade head` creates the full schema on an empty database;
  `alembic upgrade head` on the existing stack reports no pending upgrades;
  app still boots via create_all fallback; tests pass.

## Risks

- Autogenerate may miss server-side defaults or enum types — review the
  generated file line by line before committing.
- Do not change `DATABASE_URL` handling; env.py must reuse `database.engine`
  to avoid a second connection-config path.
