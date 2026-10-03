# Plan 04 — Dev environment fixes

- **Wave:** 1 (no dependency on Plan 01 — can start immediately)
- **Depends on:** nothing
- **Priority:** P1 — the documented dev workflow is broken

## Objective

Make `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`
actually work for live development, and remove tracked cruft.

## Context

- `docker-compose.dev.yml` frontend override runs `command: npm start` inside
  the **nginx-based production image** (no npm/node in that image) and mounts
  `./frontend/src` etc. into `/app` — the mounts land in the nginx html root,
  not a node project.
- `backend/tmp.Dockerfile` is tracked in git despite `.gitignore` containing
  `*tmp.Dockerfile` (it was committed before the rule / force-added).
- `backend/main.py:59` CORS default includes `http://localhost:3000` (dead
  CRA port); Vite dev serves on 5173.
- The `./frontend/public` mount was already fixed to `index.html` in a prior
  session — keep that fix.

## Tasks

1. Rewrite the frontend service in `docker-compose.dev.yml` as a proper Vite
   dev service:
   - `image: node:20-alpine` (override the built image)
   - working_dir `/app`, mount `./frontend:/app` with an anonymous volume at
     `/app/node_modules`
   - `command: sh -c "npm install && npm run dev -- --host 0.0.0.0"`
   - expose `${FRONTEND_DEV_PORT:-5173}:5173`
   - keep `CHOKIDAR_USEPOLLING=true`
   - keep the backend override (bind-mount `./backend:/app` + pip install +
     uvicorn `--reload`) as-is; it is correct.
2. Untrack and delete the stray file:
   `git rm --cached backend/tmp.Dockerfile && rm backend/tmp.Dockerfile`.
3. Update `main.py` CORS default to
   `"http://localhost:80,http://localhost:5173"` (keep 80 for the nginx
   container).
4. Verify the dev stack boots: backend reloads on source change, frontend Vite
   dev server responds on 5173 with HMR working (edit a component and watch
   the browser refresh — at minimum confirm the Vite welcome/client responds).
5. Update the usage comment at the top of `docker-compose.dev.yml` with the
   correct command and ports.

## Files owned

- `docker-compose.dev.yml`
- `backend/main.py` (one line: CORS default)
- `backend/tmp.Dockerfile` (delete)

## Verification

```bash
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
curl -fsS http://localhost:5173/ | head -5        # Vite dev server
curl -fsS http://localhost:8001/health            # backend with reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
git ls-files | grep tmp.Dockerfile                # expect empty
```

## Done criteria

- Dev compose config validates; Vite dev server and reloading backend both come
  up; `tmp.Dockerfile` gone from disk and index; CORS default updated.

## Risks

- `npm install` on every dev start is slow; acceptable for dev, but note
  `npm ci` is not possible without a clean lockfile state — use `npm install`.
- The dev frontend on 5173 must be added to `CORS_ORIGINS` when running
  against a separately-running backend; document this in the file header.
