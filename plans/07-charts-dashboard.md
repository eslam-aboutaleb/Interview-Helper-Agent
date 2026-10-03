# Plan 07 — Charts dashboard + stats time series

- **Wave:** 2 (parallel-safe with 06 and 09; **not** with 08 — both edit `schemas.py`)
- **Depends on:** 01
- **Priority:** P1 — RECOMMENDATIONS.md gap: "Charts / radar dashboards"

## Objective

Extend `/api/stats/` with time-series and distribution data, and render it in
the Stats page with Recharts (radar, bar, line, area).

## Context

- `GET /api/stats/` currently returns counts + averages only
  (`StatsResponse` in `backend/schemas.py`; `routes/stats.py`).
- `frontend/src/pages/Stats.tsx` renders `StatCard`s only; no chart library
  in `frontend/package.json`.
- Data available: `users.created_at`, `answer_evaluations` (scores, timestamps),
  `questions.difficulty`, `questions.question_type`, `interview_sessions`.

## Tasks

1. **Backend** — extend `StatsResponse` and `routes/stats.py` with:
   - `signups_last_7_days`: list of `{date, count}`
   - `evaluations_last_7_days`: list of `{date, average_score, count}`
   - `difficulty_distribution`: `{1: n, 2: n, ...}` or list of `{difficulty, count}`
   - `questions_by_type` already exists — keep
   - `average_score_trend` per week (last 8 weeks) if evaluation data exists
   Use efficient SQL (`func.date_trunc` / `func.count` group-bys), not
   Python-side loops over full tables.
2. **Backend tests** — extend `tests/test_stats_api.py`: empty-database shape,
   seeded data aggregation correctness, date-bucketing boundaries.
3. **Frontend** — `npm install recharts` (via node container, commit
   `package.json` + `package-lock.json`); in `Stats.tsx` add:
   - `RadarChart` of questions by type
   - `BarChart` of difficulty distribution
   - `AreaChart` of signups + evaluations over 7 days
   - `LineChart` of average score trend (hide gracefully when no data)
   Keep the existing StatCards; charts go below with the same card styling.
4. Handle the empty state (no evaluations yet) with `EmptyState`, not a blank
   chart.

## Files owned

- `backend/routes/stats.py`
- `backend/schemas.py` (StatsResponse section only — 08 appends elsewhere)
- `backend/tests/test_stats_api.py`
- `frontend/package.json`, `frontend/package-lock.json`
- `frontend/src/pages/Stats.tsx`
- `frontend/src/types/index.ts` (Stats type extension)

## Verification

```bash
cd backend && python3 -m pytest tests/test_stats_api.py -q
python3 -m ruff check backend/ && python3 -m ruff format --check backend/
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  sh -c "npm ci --no-fund --no-audit && npm run build"
curl -fsS http://localhost:8001/api/stats/ | python3 -m json.tool   # new fields present
```

## Done criteria

- Stats endpoint returns the new series; charts render with seeded data and
  degrade gracefully when empty; tests pass; build passes.

## Risks

- Postgres `date_trunc` returns timestamptz — serialize as `date.isoformat()`
  in the response schema to keep JSON stable.
- Recharts v3 may have different API than v2 examples — pin and check the
  installed version's docs.
