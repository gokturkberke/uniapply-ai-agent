**Date:** 2026-06-18
**Topic:** Frontend Docker docs cleanup (PR 3 follow-up)
**Motivation:** Post-PR-3 review found one stale README sentence after adding the frontend Docker service:
the local frontend section still says "Local-dev only for now (no Docker service yet)." The Docker quickstart
and `docs/docker.md` are otherwise aligned with the new nginx single-origin compose setup. This is a docs-only
cleanup so the header carries a measurable **Goal** instead of a Hypothesis.
**Goal:** Remove stale frontend-Docker wording and verify the README/docs/env/package metadata still describe
the current full-stack compose accurately. No code, dependency, endpoint, or compose behavior change.
**Preconditions:** PR 3 branch `feat/frontend-docker` is pushed; working tree has only the pre-existing
untracked root `package-lock.json`; Docker daemon is still user-run only in this environment.

---

## 1) Clean stale README wording
- **Goal:** Make the frontend section describe local dev without contradicting the Docker full-stack section.
- **Files:** `README.md`.
- **Steps:** replace the stale "Local-dev only for now (no Docker service yet)" wording with a sentence that
  distinguishes local Vite dev (`:5173` -> API `:8000` + CORS) from Docker full-stack (`:8080` via nginx).
- **Test / verification:** `rg "no Docker service yet|Local-dev only for now"` returns no stale matches.
- **Expected outcome:** README no longer contradicts PR 3.
- **DONE / DROPPED:**

## 2) Metadata/docs consistency check
- **Goal:** Confirm no `requirements.txt`, env example, package manifest, Docker docs, or compose text needs a
  companion edit for this docs cleanup.
- **Files:** read-only unless a stale reference is found: `requirements.txt`, `.env.example`,
  `frontend/.env.example`, `frontend/package.json`, `frontend/package-lock.json`, `docs/docker.md`,
  `docker-compose.yml`, `frontend/Dockerfile`, `frontend/nginx.conf`.
- **Steps:** scan for stale Docker/frontend/API-base references; leave dependency files unchanged unless the
  scan finds a real mismatch.
- **Test / verification:** `docker compose config`; `npm run build`; `npm test`; `.venv/bin/python -m pytest`
  if no dependency files are touched. User-run Docker smoke remains unchanged.
- **Expected outcome:** docs cleanup is limited to stale wording; offline gates remain green.
- **DONE / DROPPED:**

---

## Non-goals
- No Docker runtime behavior change; no nginx/compose change.
- No dependency change (`requirements.txt`, `package.json`, lockfiles) unless inspection proves a mismatch.
- No frontend app-code change; no CORS/config/default-provider change.

## Git / workflow
- Continue on `feat/frontend-docker`. Commit this plan, then after approval commit the docs cleanup + DONE
  markers and push. Leave the unrelated root `package-lock.json` untracked.
