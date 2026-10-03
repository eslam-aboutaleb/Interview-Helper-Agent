# Plan 09 — Full-text search + import/export

- **Wave:** 2 (parallel-safe with 06 and 07; **not** with 08 — both edit
  `routes/questions.py`)
- **Depends on:** 01
- **Priority:** P1 — RECOMMENDATIONS.md gaps: "full-text search (Postgres
  tsvector)", "import/export (JSON/CSV/Anki)"

## Objective

Add a `q` full-text search parameter to the questions list endpoint, plus
export (JSON/CSV) and import (JSON) endpoints for the question bank.

## Context

- `GET /api/questions/` (`backend/routes/questions.py:133`) currently filters
  by exact `job_title`, `question_type`, `flagged_only` — no text search.
- Database is Postgres 15 (`postgres:15` in compose) — `tsvector` /
  `websearch_to_tsquery` available.
- The app also supports SQLite (in-memory, for tests) — the search
  implementation must degrade gracefully (fall back to `ILIKE` when the
  dialect is SQLite).

## Tasks

1. **Search:**
   - Add `q: Optional[str]` query param to `GET /api/questions/`.
   - Postgres path: `func.websearch_to_tsquery('english', q)` against a
     `tsvector` computed from `question_text` + `job_title` + `tags`
     (use `func.to_tsvector` on the fly — no schema change required; add a
     functional GIN index via Alembic only if Plan 03 has landed, otherwise
     skip the index and note it).
   - SQLite path: `ILIKE` across the same columns.
   - Return results ordered by relevance (Postgres) / created_at (SQLite).
   - Tests: search hit/miss, empty `q` (returns normal list), special
     characters, SQL-injection attempts (`q = "'; DROP TABLE questions;--"`).
2. **Export:**
   - `GET /api/questions/export?format=json|csv` — streams the user's
     accessible questions (all questions are shared in this app; keep the
     existing visibility model) in the chosen format; `text/csv` with proper
     quoting via the `csv` module, `application/json` via the schema list.
3. **Import:**
   - `POST /api/questions/import` accepting a JSON array of question objects
     (same shape as `QuestionCreate`); validate each entry, skip invalid ones,
     return a summary `{imported: n, skipped: n, errors: [...]}` with 207-style
     information in the body (status 200 with the summary — keep it simple).
   - Tests: valid import, partial-invalid import, empty payload (400).
4. **Frontend:**
   - `Questions.tsx`: search input (debounced, 300 ms) wired to `q` param.
   - Export button (JSON/CSV) triggering a download; Import button reading a
     JSON file and posting it, showing the summary toast.
   - `api.ts`: `questionsApi.search(q, ...)`, `questionsApi.export(format)`,
     `questionsApi.import(file)`.

## Files owned

- `backend/routes/questions.py` (search param, export, import endpoints)
- `backend/tests/test_questions_api.py`
- `frontend/src/pages/Questions.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/types/index.ts`

## Verification

```bash
cd backend && python3 -m pytest tests/test_questions_api.py -q
python3 -m ruff check backend/ && python3 -m ruff format --check backend/
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
TOKEN=$(curl -fsS -X POST http://localhost:8001/api/auth/login -H 'Content-Type: application/json' -d '{"email":"smoke@example.com","password":"password123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -fsS "http://localhost:8001/api/questions/?q=hash" -H "Authorization: Bearer $TOKEN"
curl -fsS "http://localhost:8001/api/questions/export?format=csv" -H "Authorization: Bearer $TOKEN" | head -3
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  sh -c "npm ci --no-fund --no-audit && npm run build"
```

## Done criteria

- Search works on Postgres (running stack) and SQLite (tests); export produces
  valid JSON/CSV; import handles partial failures; injection attempts are safe;
  build passes.

## Risks

- `websearch_to_tsquery` exists in Postgres 11+ — fine on postgres:15, but the
  dialect check must happen at query time (`db.bind.dialect.name`), not import
  time, so tests on SQLite still pass.
- CSV injection (formula injection via leading `=`, `+`, `-`, `@`) — prefix
  such cells with a quote or sanitize.
