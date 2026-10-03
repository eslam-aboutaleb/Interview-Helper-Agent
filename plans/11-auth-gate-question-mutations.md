# Plan 11 — Auth-gate question mutations (H1)

- **Wave:** 4a (parallel-safe with 14 — no shared files; **not** with 13 — both edit `backend/routes/questions.py`)
- **Depends on:** nothing
- **Priority:** P0 — broken access control: anonymous clients can create, modify, and delete any question in the shared bank
- **Source:** code review 2026-10-03, finding H1 (+ M8)

## Objective

Require authentication on every mutating question endpoint, matching the
documents router (already fully gated behind `get_current_user`) and the
README's stated model ("Authentication uses `Authorization: Bearer <token>`
where required; most read endpoints work anonymously").

## Context

`backend/routes/questions.py` resolves the user with `get_optional_user`
(returns `None` for anonymous callers) on six mutating endpoints, and
`POST /sets` has no user dependency at all:

| Endpoint                       | Line | Current dependency  |
| ------------------------------ | ---- | ------------------- |
| `POST /api/questions/generate` | 218  | `get_optional_user` |
| `POST /api/questions/import`   | 455  | `get_optional_user` |
| `POST /api/questions/`         | 577  | `get_optional_user` |
| `PUT /api/questions/{id}`      | 642  | `get_optional_user` |
| `DELETE /api/questions/{id}`   | 721  | `get_optional_user` |
| `POST /api/questions/rate`     | 875  | `get_optional_user` |
| `POST /api/questions/sets`     | 772  | none                |

`GET /api/questions/{id}` (line 536) is a **read** and correctly stays on
`get_optional_user` (optional history tracking) — do not change it.

`backend/deps.py` already provides `get_current_user` (401 on missing/
malformed header or invalid/expired token) and `get_current_admin_user`.

M8 is fixed by the same change: `get_optional_user` fails open (invalid
token → anonymous), which is acceptable for reads but not for writes.

## Tasks

1. Import `get_current_user` in `backend/routes/questions.py` (keep
   `get_optional_user` for the GET-by-id route).
2. Switch the six endpoints to `current_user: User = Depends(get_current_user)`.
3. Add `current_user: User = Depends(get_current_user)` to
   `create_question_set` (`POST /sets`).
4. Simplify the now-non-optional user: `current_user.id if current_user else None`
   → `current_user.id` (lines 256, 491, 611); drop the `if current_user`
   guards around `record_action` (lines 264, 521, 619, 693, 754, 913).
5. Update docstrings: `current_user: Authenticated user` (drop "(optional)")
   and add `HTTPException 401` to each Raises section.
6. Tests (`backend/tests/test_questions_api.py`): every mutating call must
   register a user and pass `auth_headers(user["token"])` (~45 call sites
   across the generate/create/update/delete/sets/rate/import classes and
   the service-level tests at lines 723–831). Read tests stay anonymous.
7. Add explicit tests: each of the seven mutations returns **401** with no
   token and **401** with an invalid token.
8. `README.md`: mark the question mutation endpoints as authenticated in
   the API tables (the "Auth — /api/auth" section and the questions table).

## Files owned

- `backend/routes/questions.py`
- `backend/tests/test_questions_api.py`
- `README.md`

## Verification

```bash
cd backend && .venv/bin/pytest tests/ -q
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
cd backend && .venv/bin/coverage run --source=. -m pytest tests/ && .venv/bin/coverage report   # ≥90%
```

## Done criteria

- All seven mutations return 401 for anonymous and invalid-token callers.
- Authenticated flows (generate/import/create/update/delete/rate/sets) pass.
- Coverage gate holds; ruff clean; no `get_optional_user` remains on any mutating route.

## Risks

- ~45 test call sites need headers — mechanical; the test run will surface any missed site.
- Frontend mutation calls will 401 until plan 12 lands. Ship 11 and 12 in the same release, or accept temporary breakage on the dev stack.
- If anonymous generation is an intentional product requirement, do **not** gate it — instead document it explicitly and add rate-limiting (see plan 15.3). Default decision: require auth.
