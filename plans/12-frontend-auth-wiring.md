# Plan 12 — Frontend auth wiring (H2)

- **Wave:** 4b (parallel-safe with 13 — disjoint file sets; **not** before 11)
- **Depends on:** 11 (the API rejects anonymous mutations; the UI must be able to authenticate)
- **Priority:** P0 — without this, `/api/documents/*` and all question mutations are unreachable from the UI (every call 401s)
- **Source:** code review 2026-10-03, finding H2

## Objective

Wire authentication end-to-end in the frontend: persist the session token,
attach it to every API request, and provide login/register pages.

## Context

Backend (`backend/routes/auth.py`), all under `/api/auth`:

- `POST /register` → 201 `TokenResponse` `{ token, user }`
- `POST /login` → 200 `TokenResponse` `{ token, user }`
- `POST /logout` → 204 (requires Bearer token; revokes the session)
- `GET /me` → 200 `UserResponse` `{ id, email, full_name?, role, created_at, last_login_at? }`

`frontend/src/services/api.ts` has only a **response** interceptor — no
request interceptor, no token storage, and no login/register page exists
anywhere in `frontend/src` (no `localStorage`/`sessionStorage` usage at
all). Every `/api/documents/*` call therefore fails with 401 from the UI.

## Tasks

1. New `src/services/auth.ts`: `getToken()` / `setToken(token)` /
   `clearToken()` over `localStorage` key `auth_token`, and
   `authApi = { login, register, logout, me }` matching the routes above.
2. `src/services/api.ts`:
   - **request** interceptor: when `getToken()` returns a value, set
     `Authorization: Bearer <token>`. Must not clobber per-request
     headers — the multipart upload in `documentsApi.upload` relies on
     `Content-Type: undefined`.
   - **response** interceptor: on 401, `clearToken()` and redirect to
     `/login` (guard against redirect loops).
3. New `src/context/AuthContext.tsx`: `AuthProvider` holding
   `{ user, token, login, register, logout }`; hydrate from localStorage
   and validate via `GET /me` on mount; export a `RequireAuth` wrapper
   for protected routes.
4. `src/types/index.ts`: add `User` and `TokenResponse` interfaces —
   copy field names from `backend/schemas.py` (`UserResponse`,
   `TokenResponse`), don't guess.
5. New `src/pages/Login.tsx` and `src/pages/Register.tsx`: controlled
   inputs matching the existing page conventions (see `Generate.tsx`),
   error toasts via `parseAxiosError`, success → redirect to `/`.
6. `src/App.tsx`: add public `/login` and `/register` routes; wrap the
   existing app routes in `RequireAuth`.
7. `src/components/Header.tsx`: show the user's email + Logout when
   authenticated; Login / Register links otherwise.

## Files owned

- `frontend/src/services/auth.ts` (new)
- `frontend/src/services/api.ts`
- `frontend/src/context/AuthContext.tsx` (new)
- `frontend/src/types/index.ts`
- `frontend/src/pages/Login.tsx` (new)
- `frontend/src/pages/Register.tsx` (new)
- `frontend/src/App.tsx`
- `frontend/src/components/Header.tsx`

## Verification

```bash
cd frontend && npm run build        # tsc --noEmit (strict) + vite build
cd frontend && npx prettier --check "src/**/*.{ts,tsx,css}"
# manual: register → login → upload/list/delete a document; reload keeps
# the session; a 401 clears the session and redirects to /login
```

## Done criteria

- `npm run build` and prettier pass; login/register/logout/me work against
  the running stack; every API request carries the Bearer token when a
  session exists; 401 clears the session and redirects.

## Risks

- The request interceptor must merge with (not replace) per-request
  `headers` — verify the multipart upload still sends no Content-Type.
- `logout` must call `POST /api/auth/logout` **before** clearing the
  local token, or session revocation silently becomes a no-op.
- Don't wrap `/login` / `/register` in `RequireAuth` (redirect loop).
- Token in localStorage is XSS-readable — acceptable for this stage;
  see plan 15.1 for the hardened alternative (httpOnly cookie).
