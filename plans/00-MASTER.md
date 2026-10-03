# Master Plan — Interview Helper Agent: Remaining Enhancements & Bug Fixes

> Created: 2026-10-03 · Repo: `Interview-Helper-Agent` (branch `master`)
> Current state: 397 backend tests passing, 97% coverage, ruff + prettier clean,
> docker stack healthy, code pushed to `origin/master`.

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
```

## Wave table & suggested agent assignment

| Wave | Plan | Title | Depends on | Parallel-safe with |
| ---- | ---- | ----- | ---------- | ------------------ |
| 0 | 01 | Dependency upgrades & vulnerability remediation | — | — (run alone) |
| 1 | 02 | CI/CD pipeline (GitHub Actions) | 01 | 03, 04, 05 |
| 1 | 03 | Alembic migrations | 01 | 02, 04, 05 |
| 1 | 04 | Dev environment fixes | — (can start immediately) | 02, 03, 05 |
| 1 | 05 | Backend coverage gaps → ≥90%/module | 01 | 02, 03, 04 |
| 2 | 06 | Skill-gap & documents frontend | — | 07, 09 (not 08: both edit `App.tsx`) |
| 2 | 07 | Charts dashboard + stats time series | 01 | 06, 09 (not 08: both edit `schemas.py`) |
| 2 | 08 | Company-specific mode + learning plan | 01 | run after 06 and 07 land (touches `App.tsx`, `schemas.py`, `models.py`, `routes/questions.py`) |
| 2 | 09 | Full-text search + import/export | 01 | 06, 07 (not 08: both edit `routes/questions.py`) |
| 3 | 10 | P2 backlog (voice, RAG, code exec, gamification, OAuth) | — | documentation only |

## File ownership matrix (wave 2)

| File | 06 | 07 | 08 | 09 |
| ---- | -- | -- | -- | -- |
| `frontend/src/services/api.ts` | ✏️ | — | — | ✏️ |
| `frontend/src/types/index.ts` | ✏️ | ✏️ | ✏️ | ✏️ |
| `frontend/src/App.tsx` | ✏️ | — | ✏️ | — |
| `frontend/src/pages/Stats.tsx` | — | ✏️ | — | — |
| `frontend/src/pages/Questions.tsx` | — | — | ✏️ (company filter) | ✏️ (search box) |
| `backend/routes/stats.py` | — | ✏️ | — | — |
| `backend/schemas.py` | — | ✏️ (StatsResponse) | ✏️ (append new classes) | — |
| `backend/models.py` | — | — | ✏️ (Question.company) | — |
| `backend/routes/questions.py` | — | — | ✏️ (company filter) | ✏️ (search + export/import) |
| `backend/services/learning_plan.py` | — | — | ✏️ (new) | — |
| `backend/routes/learning.py` | — | — | ✏️ (new) | — |
| `frontend/package.json` | — | ✏️ (recharts) | — | — |

**Rule:** if two plans claim ✏️ on the same file, run them sequentially in the
order listed in the wave table, or have the agents hand off the file.

## Global quality gates (every plan, before push)

```bash
# backend
cd backend && python3 -m ruff check . && python3 -m ruff format --check .
cd backend && ./scripts/check_coverage.sh   # enforces fail_under=90

# frontend (via docker node image — no local node/npm on this machine)
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  npx -y prettier@3 --check "src/**/*.{ts,tsx,css,js}" index.html
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  sh -c "npm ci --no-fund --no-audit && npm run build"

# docker
docker compose -f docker-compose.yml build && docker compose -f docker-compose.yml up -d
curl -fsS http://localhost:8001/health   # expect {"status":"healthy","database":"connected"}

# secrets
git ls-files | grep -iE '(^|/)\.env|secret|credential'   # expect empty
```

Environment notes: `ruff` runs as `python3 -m ruff`; `docker` is at
`/usr/local/bin/docker` (export `PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"`);
there is **no local node/npm** — use the `node:20-alpine` container.

## Definition of done (per plan)

- [ ] All tasks checked off
- [ ] Verification commands pass with expected output
- [ ] Global quality gates pass
- [ ] Changes committed with a descriptive message and pushed to `origin/master`
- [ ] Master plan updated (status column) if the plan changes scope
