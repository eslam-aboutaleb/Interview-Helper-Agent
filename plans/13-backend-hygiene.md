# Plan 13 — Backend hygiene & correctness (M1–M5, M7, L1–L4, L6, L8)

- **Wave:** 4b (parallel-safe with 12 — disjoint file sets; **not** with 11 — both edit `backend/routes/questions.py`)
- **Depends on:** 11 (shares `backend/routes/questions.py`; run after 11 lands)
- **Priority:** P1 — correctness/robustness; the only API-visible change is M4 (additive query params)
- **Source:** code review 2026-10-03

## Objective

Fix the review's medium and low backend findings: partial-write risk,
information disclosure, unbounded inputs, N+1 queries, false-positive
skill matching, and transaction-boundary smells.

## Tasks (ordered)

1. **M2 — single commit in `generate_questions`** (`routes/questions.py`
   ~253–261): `db.add` every question in the loop, then **one**
   `db.commit()` after the loop; `db.refresh` after the commit (IDs are
   needed for the history context). Today a failure at question 3 of 5
   leaves 1–2 persisted and the handler's `rollback()` cannot undo them.
2. **M1 — stop leaking internals in 500s** (`routes/questions.py` ~12
   sites, `routes/stats.py` 207–210): replace `detail=f"...: {str(e)}"`
   with a generic `"Internal server error"` detail and log the real
   exception with `logger.exception(...)`. Keep 400/404/422 details
   unchanged.
3. **M3 — cap the import payload** (`routes/questions.py`
   `import_questions`): reject `len(payload) > 1000` with a 400 (mirrors
   the `QuestionSetCreate.question_ids` cap of 1000).
4. **M4 — paginate the export** (`routes/questions.py`
   `export_questions`): add `skip`/`limit` Query params (mirror `GET /`)
   and apply `.offset().limit()`; the frontend already sends `limit`
   (silently ignored today). Also fix the `questions_json_chunks`
   docstring (**L2**) — it claims "streaming keeps memory flat" but
   `query.all()` already materialized the rows.
5. **M5 — kill the N+1 in `create_question_set`** (~800–804): one query
   `db.query(Question.id).filter(Question.id.in_(question_set.question_ids))`,
   diff against the requested IDs, and 404 listing the missing ones.
6. **M7 — word-boundary skill matching** (`services/document_service.py`
   `_find_skills` ~148–150): `re.search(rf"\b{re.escape(skill)}\b", lower)`
   instead of `skill in lower` (today `"api" in "rapid"` matches). Handle
   `c++`/`c#` explicitly — `\b` misbehaves around non-word characters.
7. **L1 — `record_action` must not commit** (`services/history_service.py`
   ~48–50): only `db.add(entry)`; let the caller commit. In
   `delete_question`, record the history entry **after** the delete
   commits (today a failed delete still logs "deleted").
8. **L3 — parser error logging** (`services/document_service.py`
   ~116–118, 132–134): `logger.exception(...)` with traceback instead of
   `logger.error`; keep returning `""` so the route's 422 still applies.
9. **L4 — CSV sanitizing of negatives** (`routes/questions.py`
   `sanitize_csv_cell` ~171–180): don't prefix a plain negative number
   (`-5`); only prefix `-` when followed by a non-digit (formula-injection
   shapes like `=-1+1`).
10. **L6 — type hints**: `apply_question_filters(query: Query, ...)`,
    `_day_bucket(column: ColumnElement, ...)` (import from
    `sqlalchemy.orm` / `sqlalchemy.sql.elements`).
11. **L8 — expunge failed imports** (`import_questions` except path
    ~502–510): `db.expunge(question)` in the `except` so a failed entry
    can't be re-flushed by the final `db.commit()`.
12. Tests for each change: single-commit behavior, import cap 400, export
    pagination, set-creation 404 with missing IDs, skill-gap word
    boundaries (assert `"api"` does **not** match `"rapid"`), CSV negative
    numbers, expunge-on-failure.

## Files owned

- `backend/routes/questions.py`
- `backend/routes/stats.py`
- `backend/services/document_service.py`
- `backend/services/history_service.py`
- `backend/tests/test_questions_api.py`
- `backend/tests/test_documents_api.py`
- `backend/tests/test_document_service.py` (if present; otherwise add cases to the documents API tests)

## Verification

```bash
cd backend && .venv/bin/pytest tests/ -q
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
cd backend && .venv/bin/coverage run --source=. -m pytest tests/ && .venv/bin/coverage report   # ≥90%
```

## Done criteria

- All listed findings fixed with tests; no 500 response contains `str(e)`;
  import/export bounded; no per-question commits; skill matching uses word
  boundaries; coverage gate holds.

## Risks

- M1 changes 500 response bodies — any test asserting on 500 `detail`
  text must be updated to the generic message.
- M7 changes skill-gap results (fewer false positives) — existing
  skill-gap test expectations may need updating.
- L1 moves the commit boundary: verify history entries still appear after
  successful operations.
