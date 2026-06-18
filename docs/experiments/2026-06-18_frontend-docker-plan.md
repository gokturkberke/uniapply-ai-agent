**Date:** 2026-06-18
**Topic:** Frontend Dockerization / full-stack compose (roadmap PR 3)
**Motivation:** The frontend runs only in local dev; the frontend milestone deferred its Dockerization. The
backend already ships a Docker stack (`docker-compose.yml`: `api` + `qdrant`). This slice adds the frontend as
a third service so the whole product comes up with one `docker compose up`, served as a production-style static
build behind nginx. Delivery/infra slice, so the header carries a measurable **Goal** instead of a Hypothesis.
**Goal:** `docker compose up --build` brings up qdrant + api + frontend; `http://localhost:8080` serves the
assistant UI with API calls reverse-proxied to the `api` service (single origin, no CORS in Docker), with no
frontend application-code change. Local dev (Vite 5173 -> api 8000 + CORS) is unchanged.
**Preconditions:** PR 2 merged to `main`; branch `feat/frontend-docker` off `main`; Node + npm available;
Docker daemon required only for the user-run build/up (it is down in this environment, so build/up are
user-run and validated here via offline `docker compose config`).

Chosen architecture (user-approved): nginx reverse proxy, single origin. Frontend builds with
`VITE_API_BASE_URL=/api`; nginx serves the SPA and proxies `/api/` -> `http://api:8000/`. No frontend code
change - `apiBaseUrl()` (`frontend/src/api/client.ts`) already returns the configured base, so calls become
`/api/health`, `/api/ask`, etc.

---

## 1) Frontend image + nginx config
- **Goal:** A small production image that builds the SPA and serves it behind nginx with an API proxy.
- **Files:** `frontend/Dockerfile` (new), `frontend/nginx.conf` (new), `frontend/.dockerignore` (new).
- **Steps:** multi-stage Dockerfile - stage `node:20-alpine` (`COPY package*.json`, `npm ci`, `COPY .`,
  `ARG VITE_API_BASE_URL=/api` + `ENV`, `npm run build`), stage `nginx:alpine` (copy `nginx.conf` to
  `/etc/nginx/conf.d/default.conf`, `--from=build /app/dist` to `/usr/share/nginx/html`, `EXPOSE 80`).
  nginx.conf: `location /api/ { proxy_pass http://api:8000/; }` (trailing slash strips `/api`) +
  `location / { root /usr/share/nginx/html; try_files $uri /index.html; }`. `.dockerignore`: `node_modules`,
  `dist`, `.vite`, `.env*`.
- **Test / verification:** `npm run build` succeeds (same build the image runs); image build is user-run.
- **Expected outcome:** static SPA served on :80 with `/api/*` proxied to the api service.
- **DONE (commit `3462a8b`):** Added `frontend/Dockerfile` (multi-stage node build -> nginx),
  `frontend/nginx.conf` (`/api/` -> `http://api:8000/` proxy + SPA fallback), and `frontend/.dockerignore`.
  `npm run build` green (same build the image runs); image build itself is user-run (daemon down). Shipped.

## 2) Compose frontend service
- **Goal:** Wire the frontend into the stack.
- **Files:** `docker-compose.yml`.
- **Steps:** add `frontend` (`build: {context: ./frontend, args: {VITE_API_BASE_URL: /api}}`, `ports:
  ["8080:80"]`, `depends_on: {api: {condition: service_healthy}}`). `api`/`qdrant` unchanged.
- **Test / verification:** `docker compose config` parses and shows the service + build arg + healthy gate.
- **Expected outcome:** one `docker compose up` starts qdrant + api + frontend.
- **DONE (commit `3462a8b`):** Added the `frontend` compose service (build arg `VITE_API_BASE_URL=/api`,
  `8080:80`, `depends_on api: condition: service_healthy`). `docker compose config` parses and shows the
  service with the arg + healthy gate. Shipped.

## 3) Docs
- **Goal:** Document the full-stack flow.
- **Files:** `README.md`, `docs/docker.md`.
- **Steps:** README Docker quickstart - UI at `http://localhost:8080`; for real answers set
  `LLM_PROVIDER=local_openai` in `.env` (host Ollama); the header provider chip shows mock vs the model.
  docker.md - a "Frontend (full stack)" section: single-origin proxy, :8080, why no CORS in Docker, build
  bakes `VITE_API_BASE_URL=/api`.
- **Test / verification:** docs match the compose/nginx wiring.
- **Expected outcome:** a reviewer can bring up the full stack from the README.
- **DONE (commit `500fc69`):** README Docker quickstart + `docs/docker.md` document the full-stack compose
  (UI at :8080, single-origin `/api` proxy, no Docker CORS, `LLM_PROVIDER=local_openai` for real answers,
  provider chip), incl. a frontend troubleshooting bullet. Shipped.

## 4) Verification + close-out
- **Goal:** Prove it offline + document the user-run path.
- **Files:** this plan file.
- **Steps:** `docker compose config` (offline) confirms the frontend service; `npm run build` green; backend
  `pytest` + frontend `npm test` stay green (no app code changed). User-run: `docker compose up --build`,
  open `:8080`, ask -> grounded answer; `curl localhost:8080/api/health` returns health JSON. Fill DONE
  markers; push.
- **Test / verification:** offline gates green; user-run steps documented.
- **Expected outcome:** full-stack compose verified offline; build/up runbook recorded.
- **DONE (verified at `500fc69`):** Offline gates green - `docker compose config` valid, frontend
  `npm run build` builds, backend `pytest` 125 passed, frontend `npm test` 14 passed (no app code changed).
  **User-run (Docker daemon was down in this environment):** `docker compose up --build`, open
  `http://localhost:8080` (UI loads, provider chip shows the active provider), pick a programme + ask -> a
  grounded answer proxied through nginx with no CORS; `curl localhost:8080/api/health` mirrors
  `localhost:8000/health`. Shipped on `feat/frontend-docker`.

---

## Non-goals
- No frontend app-code change; no CORS change (local dev keeps PR 1 CORS; Docker uses the proxy).
- No change to `api`/`qdrant` beyond adding `frontend`; no new endpoints; no default-provider change.
- No automated Docker-build CI test (daemon-dependent); offline `docker compose config` + `npm run build` are
  the gate. Not bundling index/model into images.

## Git / workflow
- Branch `feat/frontend-docker` off `main`. Commit order: this plan -> image + nginx (item 1) -> compose
  (item 2) -> docs (item 3) -> DONE markers (item 4). `docker compose config` + `npm run build` + `pytest`
  green; push + PR.

## Files touched
- New: `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/.dockerignore`,
  `docs/experiments/2026-06-18_frontend-docker-plan.md`.
- Edit: `docker-compose.yml`, `README.md`, `docs/docker.md`. No app-code or dependency change.
