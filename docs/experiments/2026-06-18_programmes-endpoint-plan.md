**Date:** 2026-06-18
**Topic:** `/programmes` registry endpoint - frontend stops hardcoding the programme list (roadmap PR 4)
**Motivation:** The frontend hardcodes the 5 programmes in `frontend/src/config/programmes.ts` (slugs +
display names), duplicating data the backend already owns in the curated registry
(`data/registry/sources.json`, loaded by `load_registry()` in `app/rag/registry.py`). The frontend milestone
flagged a real `/programmes` endpoint as a future backend decision; this delivers it. Delivery + small-domain
slice, so the header carries a measurable **Goal**.
**Goal:** A read-only `GET /programmes` returns the distinct programmes (slug pair + display title) from the
registry; the frontend fetches it on load and populates the selector with no hardcoded list. No change to
retrieval scoping or the existing `/ask`-family contracts.
**Preconditions:** PR 3 merged to `main`; branch `feat/programmes-endpoint` off `main`; Node + npm available.

Registry finding: `RegisteredSource` (`app/rag/metadata.py`) has `university_slug`, `programme_slug`, and a
per-source `title`, but no separate display-name fields. Each of the 5 programmes has exactly one `primary`
source titled `"{University} - {Programme} (programme page)"`, so the endpoint derives one display `title` per
programme by stripping the trailing parenthetical - no registry schema/data change (user-approved single-title
shape).

---

## 1) Domain: distinct programmes from the registry
- **Goal:** A pure function that turns the source manifest into a de-duplicated programme list with a label.
- **Files:** `app/rag/metadata.py` (new `ProgrammeSummary`), `app/rag/registry.py` (new `distinct_programmes`).
- **Steps:** `ProgrammeSummary(BaseModel)` = `university_slug`, `programme_slug`, `title`.
  `distinct_programmes(sources) -> list[ProgrammeSummary]`: group sources with a non-null `programme_slug` by
  `(university_slug, programme_slug)`; per group prefer a `primary` source's title (else first); strip a
  trailing parenthetical (`re.sub(r"\s*\([^)]*\)\s*$", "", title)`); return sorted by the slug pair.
- **Test / verification:** `tests/test_registry.py` - 5 programmes, titles stripped, sorted/distinct, None excluded.
- **Expected outcome:** deterministic programme list derived from the committed manifest.
- **DONE / DROPPED:**

## 2) Endpoint `GET /programmes`
- **Goal:** Expose the programme list read-only.
- **Files:** `app/api/schemas.py` (reference `ProgrammeSummary` as the response item, like `Citation`/
  `ChecklistItem` are reused), `app/api/routes.py`.
- **Steps:** `GET /programmes` (`tags=["system"]`, `response_model=list[ProgrammeSummary]`): `load_registry()`
  -> `distinct_programmes(...)`. No scope params, no new Settings, no caching (9-entry manifest).
- **Test / verification:** `tests/test_api.py` - 200 with 5 items and a known `{university_slug, programme_slug,
  title}` (Konstanz). Offline (`load_registry` reads the committed manifest).
- **Expected outcome:** `curl /programmes` returns the 5 programmes.
- **DONE / DROPPED:**

## 3) Frontend: fetch the list (remove the hardcoded array)
- **Goal:** The selector is populated from the backend; no hardcoded programmes.
- **Files:** `frontend/src/api/types.ts` (`ProgrammeInfo`), `frontend/src/api/endpoints.ts` (`getProgrammes`),
  `frontend/src/config/programmes.ts` (drop `PROGRAMMES`; keep `programmeKey`; `Programme` = alias of
  `ProgrammeInfo`), `frontend/src/App.tsx` (fetch on mount via `useApiCall(getProgrammes)`; pass list to the
  selector; resolve selection from the list; loading/error states), `frontend/src/components/
  ProgrammeSelector.tsx` (take a `programmes` prop; show `title`), `frontend/src/components/ChecklistPanel.tsx`
  (show `title` instead of `university - programme`).
- **Test / verification:** see item 4.
- **Expected outcome:** UI selector lists the backend programmes; gate + tools unchanged.
- **DONE / DROPPED:**

## 4) Tests + verification + close-out
- **Goal:** Lock the behavior and prove end to end.
- **Files:** `frontend/src/__tests__/ProgrammeSelector.test.tsx` (now takes a `programmes` prop fixture),
  `frontend/src/__tests__/App.test.tsx` (mock `getProgrammes`; selector populated + gate + a loading/error
  case).
- **Steps:** `pytest`, `npm test`, `npm run build` green; local E2E - `make run-local` + `npm run dev`, the
  selector is populated from the backend, picking one + asking works; `curl localhost:8000/programmes` lists 5.
  Fill DONE markers; push.
- **Test / verification:** all gates green; E2E recorded.
- **Expected outcome:** frontend has no hardcoded programme list; both suites green.
- **DONE / DROPPED:**

---

## Non-goals
- No registry schema/data change (derive the label from the existing `title`); no display-name fields.
- No change to `/ask`/`/checklist`/`/detect-missing`/`/draft-email` contracts or scope semantics; no new Settings.
- No caching/pagination/auth on `/programmes`; the slug-validated anti-blending guarantee is untouched
  (the endpoint only lists; retrieval scoping is unchanged).

## Git / workflow
- Branch `feat/programmes-endpoint` off `main`. Commit order: this plan -> backend (items 1-2 + tests) ->
  frontend (items 3 + tests) -> docs DONE markers. `pytest` + `npm test`/`build` green; push + PR.

## Files touched
- New: `docs/experiments/2026-06-18_programmes-endpoint-plan.md`.
- Backend: `app/rag/metadata.py`, `app/rag/registry.py`, `app/api/schemas.py`, `app/api/routes.py`,
  `tests/test_registry.py`, `tests/test_api.py`.
- Frontend: `frontend/src/api/types.ts`, `frontend/src/api/endpoints.ts`, `frontend/src/config/programmes.ts`,
  `frontend/src/App.tsx`, `frontend/src/components/ProgrammeSelector.tsx`,
  `frontend/src/components/ChecklistPanel.tsx`, `frontend/src/__tests__/{ProgrammeSelector,App}.test.tsx`.
  No new dependency.
