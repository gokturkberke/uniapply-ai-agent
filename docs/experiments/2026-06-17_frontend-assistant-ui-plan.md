**Date:** 2026-06-17
**Topic:** First frontend (assistant UI) for the V1 RAG backend - programme-scoped Ask + the three artifact tools
**Motivation:** The repo is backend-only (FastAPI V1 RAG, dockerized, merged to `main` via PRs #20/#21).
There is no way to use the product without curl/Swagger. This milestone adds the first usable,
portfolio-grade UI: a dashboard/tool layout (not a landing page) where the user picks a programme scope,
asks grounded questions, and runs the checklist / detect-missing / draft-email tools, with explicit
citations, refusal states, and the mandatory disclaimer. This is a delivery-layer + new-frontend slice,
not an eval experiment, so the header carries a measurable **Goal** instead of a Hypothesis.
**Goal:** A `frontend/` app (Vite + React + TypeScript + Tailwind) consumes the existing API contracts
**unchanged** and renders grounded answers, citations, and refusals correctly, with the only backend change
being CORS (browser cross-origin). No new endpoints, no schema/path/RAG changes; the offline test suite
stays green and the grounding-or-refuse guarantee is preserved.
**Preconditions:** V1 + Docker work merged to `main` (origin/main at the PR #21 merge); working tree clean;
Node.js + npm available on the host for the Vite app; backend runnable via `uvicorn app.main:app` with the
default `LLM_PROVIDER=mock` for offline demo.

This is a **frontend + minimal-CORS slice**: no new RAG features, no new endpoints, no schema changes, no
model experiments. The product guarantee is unchanged: unsupported scoped questions return exactly
`Information not found in the official documents.` with `insufficient_context: true` and empty citations.

### Decisions locked
- Branch base: merge `infra/dockerized-backend` -> `main` first, branch `feat/frontend-assistant-ui`, delete
  the old branch (the merge had already landed on `origin/main` via PRs #20/#21; reconciled locally).
- Styling: Tailwind CSS (v4, CSS-first via the `@tailwindcss/vite` plugin).
- Docker: local Vite dev this milestone; a `frontend` compose service is a deferred, separate follow-up.

---

## 1) Backend CORS (the only backend code change)
- **Goal:** Allow the browser dev origin to call the API; default behavior unchanged for non-browser clients.
- **Files:** `app/core/config.py`, `app/main.py` (`create_app`), `.env.example`, `tests/test_cors.py` (new).
- **Steps:** add a typed `cors_allow_origins: str` Setting defaulting to the Vite dev origins
  (`http://localhost:5173,http://127.0.0.1:5173`), comma-separated to avoid the pydantic-settings
  JSON-list-in-env footgun, plus a small helper that splits it to a list; in `create_app()` add
  `CORSMiddleware` with that origin list, `allow_methods=["*"]`, `allow_headers=["*"]` (no credentials -
  no cookies); document `CORS_ALLOW_ORIGINS=` in `.env.example`.
- **Test / verification:** new offline `tests/test_cors.py` asserts a request carrying an `Origin` header
  gets `access-control-allow-origin` echoed; full `pytest` stays green.
- **Expected outcome:** browser at `:5173` can call `:8000`; no schema/path/RAG change; suite green.
- **DONE / DROPPED:**

## 2) Frontend scaffold (Vite + React + TS + Tailwind v4)
- **Goal:** A minimal, reproducible frontend project that builds and runs against a configurable backend URL.
- **Files:** new `frontend/` tree (`package.json`, `vite.config.ts`, `tsconfig*.json`, `index.html`,
  `src/main.tsx`, `src/App.tsx`, `src/index.css`, `frontend/.env.example`); root `.gitignore`.
- **Steps:** scaffold via the Vite `react-ts` template; add Tailwind v4 (`@tailwindcss/vite` plugin in
  `vite.config.ts`, `@import "tailwindcss";` in `src/index.css`); pin dependency versions; add
  `frontend/.env.example` documenting `VITE_API_BASE_URL=http://localhost:8000`; add `frontend/node_modules`
  and `frontend/dist` to `.gitignore`.
- **Test / verification:** `npm run build` succeeds; `npm run dev` serves the app shell.
- **Expected outcome:** clean Vite+React+TS+Tailwind baseline, no committed `node_modules`/`dist`.
- **DONE / DROPPED:**

## 3) API layer (typed client mirroring the backend contracts)
- **Goal:** A thin, typed integration layer so panels never assume successful LLM output.
- **Files:** `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/api/endpoints.ts`,
  `frontend/src/config/programmes.ts`, `frontend/src/hooks/useApiCall.ts`.
- **Steps:** `types.ts` mirrors the Pydantic models field-for-field (`Citation { source_id; heading_path }`,
  `ChecklistItem { requirement; detail }`, and each request/response incl. `insufficient_context`,
  `confidence`, `disclaimer`, echoed slugs); `client.ts` wraps `fetch` with the base URL and throws a typed
  `ApiError` on non-2xx (incl. 422) while treating a 200 with `insufficient_context: true` as a normal body;
  `endpoints.ts` exposes `health`, `ask`, `checklist`, `detectMissing`, `draftEmail`; `programmes.ts`
  hardcodes the 5 programmes with exact slugs; `useApiCall` returns `{ data, loading, error, run }`.
- **Test / verification:** covered by the Vitest specs in item 5 (client error/200 behavior).
- **Expected outcome:** every request is scoped by the selected programme's exact slugs; refusal and
  empty-content branches are representable in types.
- **DONE / DROPPED:**

## 4) UI components (dashboard layout + the four tools)
- **Goal:** A restrained, professional tool UI: programme gate, Ask, and the three artifact tabs.
- **Files:** `frontend/src/components/` (`AppShell`, `ProgrammeSelector`, `Tabs`, `AskPanel`, `AnswerPanel`,
  `CitationsPanel`, `RefusalNotice`, `DisclaimerBar`, `ChecklistPanel`, `DetectMissingPanel`,
  `DraftEmailPanel`, `ui/{Button,Field,Spinner,ErrorBanner}`), wired in `src/App.tsx`.
- **Steps:** top bar with app name + backend health dot (`GET /health`) + programme selector; tabs disabled
  until a programme is selected; Ask routes to AnswerPanel (answer + confidence + citations) or RefusalNotice
  on `insufficient_context`; Checklist renders `items[]`; DetectMissing parses a newline textarea to
  `profile: string[]` and shows `missing`/`satisfied`; DraftEmail shows `subject`+`body` with copy; every
  result renders the `DisclaimerBar` and citation breadcrumbs (`source_id` + `heading_path`).
- **Test / verification:** manual E2E (item 6) + component specs (item 5).
- **Expected outcome:** mobile-responsive dashboard; no landing page/hero; refusal and error states explicit.
- **DONE / DROPPED:**

## 5) Frontend tests + typecheck
- **Goal:** Offline confidence in rendering logic and the client contract.
- **Files:** `frontend/src/__tests__/` specs; Vitest config (in `vite.config.ts` or `vitest.config.ts`).
- **Steps:** Vitest + React Testing Library + jsdom; specs for ProgrammeSelector gating, AskPanel grounded vs
  refusal, ChecklistPanel, DetectMissingPanel parsing, DraftEmailPanel, and `api/client` (ApiError on
  500/422, body on 200); run `tsc --noEmit` (or `vite build`) for types.
- **Test / verification:** `npm test` and the typecheck pass.
- **Expected outcome:** green suite with no live backend dependency.
- **DONE / DROPPED:**

## 6) Docs + end-to-end verification
- **Goal:** Make the frontend runnable from the README and prove the full stack works locally.
- **Files:** `README.md` (frontend quickstart section); this plan file (DONE markers).
- **Steps:** add a short "Run the frontend (local dev)" README section (`cd frontend && npm install && npm run
  dev`, the `VITE_API_BASE_URL` note, and that it talks to the local API); run the manual E2E (backend with
  mock provider + Vite dev) exercising each programme and all four tools incl. a refusal; fill DONE markers
  with commit hashes; push; clean tree.
- **Test / verification:** manual E2E checklist passes; `git status` empty after push.
- **Expected outcome:** a reviewer can run the UI in two commands and see grounded answers, citations, and
  refusals.
- **DONE / DROPPED:**

---

## Non-goals
- No new endpoints (including a `/programmes` listing - that stays a future, separate backend decision; the
  frontend hardcodes the 5 programmes for now).
- No schema/path/RAG/retrieval/model changes beyond CORS.
- No frontend Docker service (deferred follow-up); no auth, no persistence, no paid/cloud APIs.
- No marketing landing page or oversized hero; no LangGraph/agent orchestration.
- **Never committed:** `frontend/node_modules`, `frontend/dist`, `.env`, any real keys.

## Git / workflow
- Branch `feat/frontend-assistant-ui` (off `main`). Commit order: this plan file -> CORS (item 1) ->
  scaffold (item 2) -> API layer (item 3) -> UI (item 4) -> tests (item 5) -> docs + DONE markers (item 6);
  `pytest` and `npm test` green; push + PR. Working tree clean between items.

## Files touched
- New (frontend): the full `frontend/` tree (scaffold, `src/api/*`, `src/config/programmes.ts`,
  `src/hooks/useApiCall.ts`, `src/components/*`, `src/__tests__/*`, `frontend/.env.example`).
- New (backend): `tests/test_cors.py`.
- Edited (backend, small): `app/core/config.py`, `app/main.py`, `.env.example`, `README.md`.
- Repo: `.gitignore` (`frontend/node_modules`, `frontend/dist`); new plan file
  `docs/experiments/2026-06-17_frontend-assistant-ui-plan.md`. No new Python dependency.
