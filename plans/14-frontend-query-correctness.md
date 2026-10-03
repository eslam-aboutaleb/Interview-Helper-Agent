# Plan 14 — Frontend query correctness (M9)

- **Wave:** 4a (parallel-safe with 11, 12, and 13 — owns only `Questions.tsx`)
- **Depends on:** nothing
- **Priority:** P1 — filters silently drop matching questions once the bank exceeds 1000
- **Source:** code review 2026-10-03, finding M9

## Objective

Move the type and job-title filters server-side so they are correct at
any bank size, and make the React Query key reflect the filter state.

## Context

`frontend/src/pages/Questions.tsx` (lines 54–57, 145–151) fetches
`questionsApi.search(debouncedSearch, { limit: 1000 })` and then filters
`question_type` / `job_title` **client-side** with a `useMemo`. The
backend `GET /api/questions/` already supports `question_type` and
`job_title` query params, so the client-side filter is redundant and
wrong past the 1000-row fetch cap. The `queryKey`
`['questions', 'all', { q: debouncedSearch }]` also omits the filter
state, so React Query can serve a stale filtered view.

## Tasks

1. Extend the `queryKey` to include the filter state:
   `['questions', 'all', { q: debouncedSearch, question_type: selectedType, job_title: selectedJobTitle }]`.
2. Pass the filters as server-side params through the existing
   `questionsApi.search(q, params)` signature — omit `question_type` /
   `job_title` when the value is `'all'`.
3. Delete the client-side `filteredQuestions` `useMemo` (lines 145–151)
   and render `questions` directly.
4. Keep the 300 ms debounce and the existing invalidation calls.

## Files owned

- `frontend/src/pages/Questions.tsx`

## Verification

```bash
cd frontend && npm run build
cd frontend && npx prettier --check "src/**/*.{ts,tsx}"
# manual: change the type/job-title filters and confirm the network
# request carries question_type / job_title params
```

## Done criteria

- Filter changes trigger a refetch with server-side params; no client-side
  filtering remains; build + prettier pass.

## Risks

- None significant — the backend params already exist and are tested.
