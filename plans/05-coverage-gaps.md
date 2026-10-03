# Plan 05 — Backend coverage gaps → ≥90% per module

- **Wave:** 1 (after Plan 01)
- **Depends on:** 01
- **Priority:** P1 — overall coverage is 97% but five modules sit below 90%

## Objective

Raise every backend module to ≥90% line coverage, focusing on the five
under-target modules, and add a `--cov-fail-under=90` gate to `pytest.ini`.

## Context

Latest coverage report (397 tests, 97% total):

| Module | Coverage |
| ------ | -------- |
| `database.py` | 87% |
| `services/document_service.py` | 88% |
| `backend/models.py` | 89% |
| `services/llm_service.py` | 91% |
| `main.py` | 91% |

All other modules are ≥97%.

## Tasks

1. **`database.py`** (→ ≥90%): cover `_pool_class_for_url` for mysql/sqlite
   schemes, `_validate_database_url` warning branches (missing password,
   default credentials in development), `get_db` rollback paths, and the
   import-time `_verify_database_connection` failure branch (mock
   `engine.connect` to raise).
2. **`services/document_service.py`** (→ ≥90%): cover `extract_text_from_pdf`
   and `extract_text_from_docx` with real tiny fixture files (generate a
   one-page PDF via `reportlab` in a test fixture or commit a small fixture
   under `tests/fixtures/`), `extract_text` dispatch for unsupported
   extensions, `_find_skills` partial matches, `extract_years_of_experience`
   edge cases ("3+ years", "no experience"), `_extract_email` failure, and
   `compute_skill_gap` with empty/missing skill sets.
3. **`models.py`** (→ ≥90%): cover remaining `@validates` hooks and
   relationship cascade behavior for `InterviewSession`, `AnswerEvaluation`,
   `QuestionHistory`, `QuestionSet`, `UserRating`.
4. **`services/llm_service.py`** (→ ≥90%): cover the fallback chain
   (primary fails → fallback succeeds → all fail), per-provider API-key
   resolution/skipping, timeout and retry paths, and temperature passthrough.
5. **`main.py`** (→ ≥90%): cover `lifespan` startup failure (mock
   `ensure_db_initialized` to raise), CORS middleware configuration, the root
   `/` endpoint, and the `/health` 500 path (mock `get_db` session to raise).
6. Add `--cov-fail-under=90` to `backend/pytest.ini` `addopts` so the gate
   is enforced on every run.
7. Re-run the full suite and record the new per-module numbers in this file.

## Files owned

- `backend/tests/test_database_config.py`
- `backend/tests/test_documents_api.py` (or new `test_document_service.py`)
- `backend/tests/test_models.py`
- `backend/tests/test_llm_service.py`
- `backend/tests/test_app_lifecycle.py`
- `backend/pytest.ini`
- `backend/tests/fixtures/` (new, if PDF/DOCX fixtures are committed)

## Verification

```bash
cd backend && python3 -m pytest tests/ --cov=. --cov-report=term
# expect: every module ≥90%, TOTAL ≥97%, exit code 0
python3 -m ruff check . && python3 -m ruff format --check .
```

## Done criteria

- All five modules ≥90%, total ≥97%, gate enforced in pytest.ini, ruff clean.

## Risks

- PDF/DOCX fixtures must be tiny (<100 KB — pre-commit rejects larger files).
- Mocking `engine.connect` at import time is fragile; prefer patching
  `database.engine` attributes inside the test, not during collection.
