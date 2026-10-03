# Plan 06 — Skill-gap & documents frontend

- **Wave:** 2 (parallel-safe with 07 and 09; **not** with 08 — both edit `App.tsx`)
- **Depends on:** nothing (backend endpoint already exists)
- **Priority:** P1 — the skill-gap feature is backend-only; no UI can call it

## Objective

Wire the existing document/skill-gap API into the frontend: a Documents page
(upload resume/JD, list, delete) and a Skill-Gap page (pick resume + JD, view
the gap analysis).

## Context

Backend already exposes (all behind `get_current_user`):

- `POST /api/documents/upload?document_type=resume|jd` (multipart file)
- `GET /api/documents/?document_type=` — list
- `DELETE /api/documents/{id}`
- `POST /api/documents/skill-gap?resume_id=&jd_id=` → `SkillGapResponse`
  (see `backend/schemas.py` for the exact response shape)

Frontend has **no** `documentsApi` in `src/services/api.ts` and no
documents/skill-gap UI.

## Tasks

1. `src/services/api.ts`: add `documentsApi` with `upload(documentType, file)`
   (use `FormData`, do **not** set Content-Type — let the browser set the
   multipart boundary), `list(documentType?)`, `remove(id)`, `skillGap(resumeId, jdId)`.
2. `src/types/index.ts`: add `UserDocument` and `SkillGap` types matching
   `UserDocumentResponse` / `SkillGapResponse` in `backend/schemas.py`.
3. New `src/pages/Documents.tsx`: two upload dropzones (resume / JD), list of
   uploaded documents with type badge + delete, loading skeletons, error toasts
   (reuse `Alert`, `EmptyState`, `Skeleton`, `parseAxiosError`).
4. New `src/pages/SkillGap.tsx`: selects for resume + JD (populated from the
   documents query), "Analyze" button, result view rendering the gap payload
   (missing skills, matched skills, experience delta — render whatever fields
   `SkillGapResponse` defines).
5. `src/App.tsx`: register routes `/documents` and `/skill-gap`.
6. `src/components/Header.tsx`: add nav links (Documents, Skill Gap).
7. Follow existing conventions: React Query (`useQuery`/`useMutation` with
   invalidation), Tailwind classes matching current design, prettier formatting.

## Files owned

- `frontend/src/services/api.ts`
- `frontend/src/types/index.ts`
- `frontend/src/pages/Documents.tsx` (new)
- `frontend/src/pages/SkillGap.tsx` (new)
- `frontend/src/App.tsx`
- `frontend/src/components/Header.tsx`

## Verification

```bash
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  sh -c "npm ci --no-fund --no-audit && npm run build"   # tsc + vite
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine \
  npx -y prettier@3 --check "src/**/*.{ts,tsx,css}"
# manual: upload a TXT resume + JD via /documents, then run /skill-gap
```

## Done criteria

- `npm run build` (tsc strict) passes; prettier clean; upload → list → delete
  and skill-gap analysis work end-to-end against the running stack.

## Risks

- Multipart upload through nginx: confirm `client_max_body_size` in
  `frontend/nginx.conf` allows resume-sized files (default 1 MB may be too
  small — raise to 10m if needed; that file is owned here too if changed).
- `SkillGapResponse` field names must be mirrored exactly in the TS type —
  copy them from `backend/schemas.py`, don't guess.
