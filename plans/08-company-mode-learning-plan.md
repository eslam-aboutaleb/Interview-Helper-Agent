# Plan 08 — Company-specific question mode + AI learning plan

- **Wave:** 2 — run **after** 06 and 07 have landed (touches `App.tsx`,
  `schemas.py`, `models.py`, `routes/questions.py`)
- **Depends on:** 01, 06, 07
- **Priority:** P1 — RECOMMENDATIONS.md gaps: "Company-specific question mode",
  "Learning plan / study roadmap"

## Objective

Two features: (a) tag questions with a company and filter by it; (b) generate a
personalized study plan from the user's skill gaps and weak areas.

## Context

- `Question` model (`backend/models.py`) has `job_title`, `question_type`,
  `difficulty`, `tags` — no company field.
- `GET /api/questions/` supports `job_title`, `question_type`, `flagged_only`
  filters (`backend/routes/questions.py:133`).
- `document_service.compute_skill_gap()` produces gap data; evaluation scores
  live in `AnswerEvaluation`.
- `services/llm_service.py` (LiteLLM) is the abstraction for AI calls with a
  fallback chain; `services/evaluation_service.py` shows the pattern of
  LLM-first with heuristic fallback.

## Tasks

1. **Company mode:**
   - `models.py`: add `company: Optional[str]` column to `Question` (indexed,
     nullable, max length via `String(100)`).
   - `schemas.py`: add `company` to create/update/response schemas; add
     `company` filter param to the list endpoint (`routes/questions.py`).
   - Add `GET /api/questions/companies/` returning distinct companies
     (mirror the existing `job-titles/` endpoint pattern).
   - Tests: create/filter/list companies endpoint.
2. **Learning plan:**
   - New `services/learning_plan.py`: `generate_learning_plan(user_id, db)` →
     gather skill gaps (latest resume-vs-JD analysis if available), weakest
     question types (from `AnswerEvaluation` averages), and produce a
     structured plan: list of `{topic, reason, recommended_question_ids,
priority, estimated_hours}`. LLM call via `LLMService` with a
     **deterministic heuristic fallback** (no LLM key configured → rule-based
     plan from the same data), following the `evaluation_service.py` pattern.
   - New `routes/learning.py`: `GET /api/learning/plan` (auth required) and
     `POST /api/learning/plan` (force regenerate). Register in `main.py`.
   - `schemas.py`: `LearningPlanResponse` etc. (append at end of file — 07
     owns the StatsResponse section).
   - Tests: heuristic fallback path, LLM path with a fake service, 401 without
     auth, empty-data plan.
3. **Frontend:**
   - `Questions.tsx`: company filter dropdown (next to job-title filter).
   - `Generate.tsx`: optional company input.
   - New `pages/LearningPlan.tsx`: fetch plan, render as an ordered checklist
     with priority badges; "Regenerate" button.
   - `App.tsx`: `/learning-plan` route; `Header.tsx`: nav link.
   - `api.ts`: `learningApi.get()/regenerate()`, `questionsApi.getCompanies()`.

## Files owned

- `backend/models.py`, `backend/schemas.py` (append), `backend/routes/questions.py`
  (company filter + companies endpoint), `backend/routes/learning.py` (new),
  `backend/services/learning_plan.py` (new), `backend/main.py` (router registration),
  `backend/tests/test_learning_api.py` (new), `backend/tests/test_questions_api.py`
  (company cases)
- `frontend/src/pages/Questions.tsx`, `frontend/src/pages/Generate.tsx`,
  `frontend/src/pages/LearningPlan.tsx` (new), `frontend/src/App.tsx`,
  `frontend/src/components/Header.tsx`, `frontend/src/services/api.ts`,
  `frontend/src/types/index.ts`

## Verification

```bash
cd backend && python3 -m pytest tests/ -q --cov=. --cov-fail-under=90
python3 -m ruff check backend/ && python3 -m ruff format --check backend/
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
docker compose -f docker-compose.yml build backend && docker compose -f docker-compose.yml up -d
curl -fsS http://localhost:8001/api/questions/companies/ -H "Authorization: Bearer $TOKEN"
curl -fsS http://localhost:8001/api/learning/plan -H "Authorization: Bearer $TOKEN"
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  sh -c "npm ci --no-fund --no-audit && npm run build"
```

## Done criteria

- Company filter + companies endpoint work; learning plan returns a structured
  plan with and without an LLM key; all tests pass; build passes.

## Risks

- Adding a column to `Question` requires a migration — coordinate with Plan 03
  (Alembic): if 03 has landed, generate a migration; otherwise `create_all()`
  will NOT add the column to an existing table, so the dev DB must be
  recreated (`docker compose down -v`) — note this in the PR description.
- The LLM prompt must request strict JSON; reuse the tolerant parsing from
  `evaluation_service._parse_llm_evaluation`.
