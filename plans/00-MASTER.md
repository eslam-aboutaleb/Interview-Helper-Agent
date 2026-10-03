# Master Plan — Interview Helper Agent: Remaining Enhancements & Bug Fixes

> Created: 2026-10-03 · Repo: `Interview-Helper-Agent`
> Branch: `wave0-1-and-plan06` (tracks `origin/wave0-1-and-plan06`)
> Current state: 604 backend tests passing, 96% coverage, ruff +
> prettier clean, `tsc` strict build clean. Waves 0–2 are fully
> landed (CI, Alembic, skill-gap/documents UI, charts, company
> mode + learning plan, search/import/export all present in the
> tree). Wave 4 (code-review remediation, plans 11–14) executed
> 2026-10-04.

## How to use this plan set

- Each `NN-*.md` file is **self-contained** and executable by one agent: objective,
  context, ordered tasks, file ownership, verification commands, done criteria.
- Plans are grouped into **waves**. Waves are sequential; plans **within** a wave
  may run in parallel **only if** their file-ownership rows don't collide
  (see the ownership matrix below).
- Before pushing, every plan must pass the **global quality gates** (bottom of
  this file).
- When a plan is finished, the agent should report: what changed, verification
  output, and any deviation from the plan.

## Current known problems (why these plans exist)

1. **152 Dependabot vulnerabilities (2 critical)** — backend pins are old
   (fastapi 0.104.1, uvicorn 0.24.0, sqlalchemy 2.0.23, pydantic 2.5.0,
   PyPDF2 3.0.1 which is EOL, python-multipart 0.0.6).
2. **No CI/CD** — `.github/` does not exist; pre-commit config is local-only.
3. **No Alembic migrations** — `alembic.ini` exists but there is no
   `alembic/versions/`; tables are created via `Base.metadata.create_all()`.
4. **Dev compose frontend is broken** — `docker-compose.dev.yml` runs
   `npm start` inside the nginx-based production image and mounts the deleted
   `frontend/public` path (path already fixed; command/image still wrong).
5. **Coverage gaps** — `database.py` 87%, `document_service.py` 88%,
   `models.py` 89%, `llm_service.py` 91%, `main.py` 91% (target ≥90% each).
6. **Stray tracked file** — `backend/tmp.Dockerfile` is committed even though
   `.gitignore` has `*tmp.Dockerfile`.
7. **Dead CORS default** — `main.py` default origins include `localhost:3000`
   (old CRA port); Vite dev runs on 5173.
8. **Skill-gap feature is backend-only** — `POST /api/documents/skill-gap`
   exists but `frontend/src/services/api.ts` has no `documentsApi` and there is
   no Documents/SkillGap UI.
9. **No full-text search, no import/export, no charts, no company-specific
   mode, no learning-plan generation** (P1 items from RECOMMENDATIONS.md).

## Status (2026-10-04)

All of waves 0–2 and wave 4 are landed on `wave0-1-and-plan06`:

- Plan 08 (company-specific mode + AI learning plan) landed via
  merge commit `d4924e9` (branch `plan-08-company-learning`,
  commit `4f3e6ac`, also pushed). Verified before merge: 584
  tests, ruff/coverage/prettier/`tsc` clean, alembic
  upgrade/downgrade round-trip on the new `company` migration
  (`8f3c1a6d4b72`). Its two new 500-detail leaks were fixed
  before the merge (generic "Internal server error" +
  `logger.exception` in `routes/learning.py` and
  `get_companies`).
- Plan 11 (`6857e49`): all seven question mutations require
  `get_current_user`; 401 for anonymous and invalid-token
  callers; README auth table updated.
- Plan 14 (`2c9ef3c`): all three Questions-page filters
  (`question_type`, `job_title`, `company`) refetch
  server-side; `filteredQuestions` useMemo deleted.
- Plan 12 (`c7f3636`): token persistence, request/response
  interceptors, `AuthContext`/`RequireAuth`, Login/Register
  pages, Header auth UI.
- Plan 13 (`40ddeb2`): M1–M5, M7, L1–L4, L6, L8 fixed with
  tests; 604 tests, 96% coverage.

Wave 4 execution adjustments (2026-10-04):

- **Plan 13 M1 scope narrowed**: `routes/learning.py` and
  `get_companies` were fixed before the plan-08 merge, so M1
  covered `routes/questions.py` (~12 sites) and
  `routes/stats.py` only.
- **Plan 13 L1 caller fixes extended**: `record_action` no
  longer commits, so every caller must. Besides the seven
  `routes/questions.py` sites, the three `services/interview_service.py`
  call sites (session_started / session_completed /
  question_asked) relied on the internal commit and now commit
  after `record_action`.
- **Plan 14 scope extended**: plan 08's company filter joined
  `question_type`/`job_title` in the server-side move;
  `QuestionSearchParams` gained a `company` field.
- **Plan 11 test-update burden**: on FastAPI 0.115.14 the
  auth dependency is solved *before* body validation, so
  422-expecting mutation tests also needed `auth_headers`
  (the "422 survives unchanged" assumption does not hold on
  this version). DB-error tests needed scoped patches because
  `get_current_user` commits (refreshes `last_used_at`).

## Code-review findings (2026-10-03) → wave 4

**0 critical, 2 high, 9 medium, 8 low.** SQL injection, XSS, CSV
injection, mass assignment, and IDOR vectors were verified safe
(parameterized queries, React auto-escaping, `sanitize_csv_cell`,
`model_dump(exclude_unset=True)`, `user_id` scoping).

- **H1** anonymous mutation of the shared question bank → plan 11
- **H2** frontend never attaches the auth token (no login UI) → plan 12
- **M1** internal exception details leaked in 500 responses → plan 13
- **M2** commit-per-question in generate (partial writes) → plan 13
- **M3** unbounded `/import` payload → plan 13
- **M4** unbounded `/export`; frontend `limit` silently ignored → plan 13
- **M5** N+1 ID verification in `create_question_set` → plan 13
- **M6** unbounded document upload — **already fixed** (`edb4d72`, 413)
- **M7** substring skill matching → false positives → plan 13
- **M8** `get_optional_user` fails open on mutations → plan 11
- **M9** client-side filtering over a 1000-row fetch → plan 14
- **L1–L4, L6, L8** transaction/logging/cosmetic fixes → plan 13
- **L5** PII plaintext at rest, **L7** skill-gap POST→GET, **H1-alt**
  anonymous generation → plan 15 (deferred — need design decisions)

## Dependency graph

```
Wave 0 (blocker)
  01-dependency-upgrades
        │
        ▼
Wave 1 (parallel, independent of each other)
  02-ci-cd-pipeline   03-alembic-migrations   04-dev-environment-fixes   05-coverage-gaps
        │
        ▼
Wave 2 (parallel feature work — respect file ownership matrix)
  06-skill-gap-frontend   07-charts-dashboard   08-company-mode-learning-plan   09-search-import-export
        │
        ▼
Wave 3 (unscheduled backlog, documentation only)
  10-p2-backlog
         │
         ▼
Wave 4 (code-review remediation — plans 11–14)
  Wave 4a (parallel — no shared files)
    11-auth-gate-question-mutations   14-frontend-query-correctness
         │
         ▼
  Wave 4b (parallel — disjoint file sets)
    12-frontend-auth-wiring   13-backend-hygiene
         │
         ▼
Wave 5 (review backlog, documentation only)
  15-review-backlog
```

## Wave table & suggested agent assignment

| Wave | Plan | Title                                                   | Depends on                | Parallel-safe with                                                                             |
| ---- | ---- | ------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------- |
| 0    | 01   | Dependency upgrades & vulnerability remediation         | —                         | — (run alone)                                                                                  |
| 1    | 02   | CI/CD pipeline (GitHub Actions)                         | 01                        | 03, 04, 05                                                                                     |
| 1    | 03   | Alembic migrations                                      | 01                        | 02, 04, 05                                                                                     |
| 1    | 04   | Dev environment fixes                                   | — (can start immediately) | 02, 03, 05                                                                                     |
| 1    | 05   | Backend coverage gaps → ≥90%/module                     | 01                        | 02, 03, 04                                                                                     |
| 2    | 06   | Skill-gap & documents frontend                          | —                         | 07, 09 (not 08: both edit `App.tsx`)                                                           |
| 2    | 07   | Charts dashboard + stats time series                    | 01                        | 06, 09 (not 08: both edit `schemas.py`)                                                        |
| 2    | 08   | Company-specific mode + learning plan                   | 01                        | run after 06 and 07 land (touches `App.tsx`, `schemas.py`, `models.py`, `routes/questions.py`) |
| 2    | 09   | Full-text search + import/export                        | 01                        | 06, 07 (not 08: both edit `routes/questions.py`)                                               |
| 3    | 10   | P2 backlog (voice, RAG, code exec, gamification, OAuth) | —                         | documentation only                                                                             |
| 4a   | 11   | Auth-gate question mutations (H1, M8)                   | —                         | 14 (not 13: both edit `routes/questions.py`)                                                   |
| 4a   | 14   | Frontend query correctness (M9)                         | —                         | 11, 12, 13 (owns only `Questions.tsx`)                                                         |
| 4b   | 12   | Frontend auth wiring (H2)                               | 11                        | 13 (disjoint file sets)                                                                        |
| 4b   | 13   | Backend hygiene (M1–M5, M7, L1–L4, L6, L8)              | 11                        | 12 (disjoint file sets)                                                                        |
| 5    | 15   | Review backlog (L5, L7, H1 alternative)                 | wave 4                    | documentation only                                                                             |

## File ownership matrix (wave 2)

| File                                | 06  | 07                 | 08                      | 09                          |
| ----------------------------------- | --- | ------------------ | ----------------------- | --------------------------- |
| `frontend/src/services/api.ts`      | ✏️  | —                  | —                       | ✏️                          |
| `frontend/src/types/index.ts`       | ✏️  | ✏️                 | ✏️                      | ✏️                          |
| `frontend/src/App.tsx`              | ✏️  | —                  | ✏️                      | —                           |
| `frontend/src/pages/Stats.tsx`      | —   | ✏️                 | —                       | —                           |
| `frontend/src/pages/Questions.tsx`  | —   | —                  | ✏️ (company filter)     | ✏️ (search box)             |
| `backend/routes/stats.py`           | —   | ✏️                 | —                       | —                           |
| `backend/schemas.py`                | —   | ✏️ (StatsResponse) | ✏️ (append new classes) | —                           |
| `backend/models.py`                 | —   | —                  | ✏️ (Question.company)   | —                           |
| `backend/routes/questions.py`       | —   | —                  | ✏️ (company filter)     | ✏️ (search + export/import) |
| `backend/services/learning_plan.py` | —   | —                  | ✏️ (new)                | —                           |
| `backend/routes/learning.py`        | —   | —                  | ✏️ (new)                | —                           |
| `frontend/package.json`             | —   | ✏️ (recharts)      | —                       | —                           |

**Rule:** if two plans claim ✏️ on the same file, run them sequentially in
the order listed in the wave table, or have the agents hand off the file.

## File ownership matrix (wave 4)

| File                                    | 11  | 12       | 13  | 14  |
| --------------------------------------- | --- | -------- | --- | --- |
| `backend/routes/questions.py`           | ✏️  | —        | ✏️  | —   |
| `backend/routes/stats.py`               | —   | —        | ✏️  | —   |
| `backend/services/document_service.py`  | —   | —        | ✏️  | —   |
| `backend/services/history_service.py`   | —   | —        | ✏️  | —   |
| `backend/tests/test_questions_api.py`   | ✏️  | —        | ✏️  | —   |
| `backend/tests/test_documents_api.py`   | —   | —        | ✏️  | —   |
| `README.md`                             | ✏️  | —        | —   | —   |
| `frontend/src/services/api.ts`          | —   | ✏️       | —   | —   |
| `frontend/src/services/auth.ts` (new)   | —   | ✏️       | —   | —   |
| `frontend/src/context/AuthContext.tsx`  | —   | ✏️ (new) | —   | —   |
| `frontend/src/types/index.ts`           | —   | ✏️       | —   | —   |
| `frontend/src/pages/Login.tsx` (new)    | —   | ✏️       | —   | —   |
| `frontend/src/pages/Register.tsx` (new) | —   | ✏️       | —   | —   |
| `frontend/src/App.tsx`                  | —   | ✏️       | —   | —   |
| `frontend/src/components/Header.tsx`    | —   | ✏️       | —   | —   |
| `frontend/src/pages/Questions.tsx`      | —   | —        | —   | ✏️  |

**Rule:** 11 and 13 share `routes/questions.py` and its tests — run 11
first, then 13. 12 and 13 are disjoint and may run in parallel after 11.
14 is independent and may run at any time.

## Global quality gates (every plan, before push)

```bash
# backend (venv lives at backend/.venv — ruff 0.6.9, pytest 8.4.2)
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
cd backend && .venv/bin/coverage run --source=. -m pytest tests/ && .venv/bin/coverage report   # fail_under=90

# frontend (system node v26 — run directly, no docker needed)
cd frontend && npx prettier --check "src/**/*.{ts,tsx,css,js}" index.html
cd frontend && npm run build   # tsc --noEmit (strict) + vite build

# docker — NOT installed on this machine; run in CI or on a docker host
docker compose -f docker-compose.yml build && docker compose -f docker-compose.yml up -d
curl -fsS http://localhost:8001/health   # expect {"status":"healthy","database":"connected"}

# secrets
git ls-files | grep -iE '(^|/)\.env|secret|credential'   # expect empty
```

Environment notes (updated 2026-10-03): backend tooling lives in
`backend/.venv` (Python 3.11) — run `.venv/bin/ruff`, `.venv/bin/pytest`,
`.venv/bin/coverage` from `backend/`. Node v26 and npm are installed
system-wide — run `npx prettier` and `npm run build` directly in
`frontend/`. **Docker is not installed on this machine** — skip the
compose gates locally; verify the API with `uvicorn main:app` + SQLite
instead. No LLM API keys are set locally, so `/generate` degrades to 503
(set `GEMINI_API_KEY` in `.env` for real responses).

## Definition of done (per plan)

- [ ] All tasks checked off
- [ ] Verification commands pass with expected output
- [ ] Global quality gates pass
- [ ] Changes committed with a descriptive message and pushed to `origin`
- [ ] Master plan updated (status column) if the plan changes scope
