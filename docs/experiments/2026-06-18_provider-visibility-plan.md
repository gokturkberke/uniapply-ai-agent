**Date:** 2026-06-18
**Topic:** Demo ergonomics + runtime provider visibility (roadmap PR 1)
**Motivation:** With the default `LLM_PROVIDER=mock`, every `/ask` and artifact call returns the refusal
state by design (mock emits no citations; the grounding guard at `app/rag/generation.py:296-298` refuses any
uncited answer). Nothing in the running product shows which provider is active, so a casual
`uvicorn app.main:app` run looks broken (observed live on 2026-06-17; switching to `local_openai` + qwen3:1.7b
produced grounded, correctly-scoped answers). This is a delivery-layer + frontend slice, so the header carries
a measurable **Goal** instead of a Hypothesis.
**Goal:** The active LLM provider/model is visible at runtime (`/health` + a UI badge), the UI warns clearly
when the provider is `mock` (demo stub that refuses), and a one-command `make run-local` starts the API with
the local model. No RAG behavior change; the only contract change is two additive `HealthResponse` fields.
**Preconditions:** Frontend milestone merged to `main`; working tree clean; Node + npm available; Ollama on
the host for the local-model demo.

This does not change retrieval, generation, or the default provider (`mock` stays the offline/CI default); it
only makes the provider visible and easy to switch. Over-refusal of the artifact tools is out of scope (PR 2).

---

## 1) Expose provider/model on `/health`
- **Goal:** Surface the active LLM provider and model so the UI (and curl) can show them.
- **Files:** `app/api/schemas.py` (`HealthResponse`), `app/api/routes.py` (`health`).
- **Steps:** add `llm_provider: str` and `llm_model: str | None` to `HealthResponse`; in `health()` set
  `llm_provider=settings.llm_provider` and `llm_model=settings.local_llm_model` when provider is
  `local_openai` else `None`. Reuses existing Settings fields, so no `.env.example` change.
- **Test / verification:** `tests/test_api.py` asserts the new fields; default -> `mock`/`None`; an override
  to `local_openai` echoes the model. Offline.
- **Expected outcome:** `/health` reports the provider/model; no other contract/path/RAG change.
- **DONE / DROPPED:**

## 2) One-command local run
- **Goal:** Make it trivial to run the API with the local model (avoid the mock footgun).
- **Files:** `Makefile`.
- **Steps:** add a `run-local` target (and `.PHONY`) running uvicorn with
  `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 LOCAL_LLM_TEMPERATURE=0
  LOCAL_LLM_SEED=42` (mirrors the README local-LLM runbook; deterministic for a stable demo).
- **Test / verification:** `make -n run-local` expands to the expected command.
- **Expected outcome:** `make run-local` starts the API against host Ollama.
- **DONE / DROPPED:**

## 3) Frontend provider badge + mock warning
- **Goal:** Show the active provider/model in the header and warn when it is the mock stub.
- **Files:** `frontend/src/api/types.ts` (`HealthResponse`), `frontend/src/components/HealthDot.tsx`.
- **Steps:** add `llm_provider: string` and `llm_model: string | null` to the TS `HealthResponse`; extend the
  existing single `/health` call in `HealthDot` to render a provider chip next to the status dot:
  `local_openai` -> slate chip with the model name; `mock` -> amber `mock - demo stub` chip with a tooltip
  pointing to `make run-local`. Render only after health loads; keep it compact/responsive.
- **Test / verification:** see item 4 (frontend tests).
- **Expected outcome:** header shows `qwen3:1.7b` on local, an amber demo-stub warning on mock.
- **DONE / DROPPED:**

## 4) Tests
- **Goal:** Lock the new behavior offline.
- **Files:** `tests/test_api.py`, `frontend/src/__tests__/*`.
- **Steps:** backend asserts the two `/health` fields (default + `local_openai` override via
  `app.dependency_overrides[get_settings]`); frontend updates the `getHealth` mock in `App.test.tsx` for the
  two new fields and adds a `HealthDot` test (mock -> demo-stub warning; local_openai -> model name).
- **Test / verification:** `pytest`, `npm test`, `tsc --noEmit` green.
- **Expected outcome:** green suites, no live backend dependency.
- **DONE / DROPPED:**

## 5) Docs + verification + close-out
- **Goal:** Document the runbook and prove it end to end.
- **Files:** `README.md`, this plan file.
- **Steps:** document `make run-local` and that the UI header shows the active provider (mock = demo stub that
  refuses); run the E2E (mock shows the warning; `run-local` shows the model + a grounded answer); fill DONE
  markers with commit hashes; push.
- **Test / verification:** manual E2E + clean tree after push.
- **Expected outcome:** a reviewer can run the real-model demo in one command and see the active provider.
- **DONE / DROPPED:**

---

## Non-goals
- No fix for Checklist/Detect-missing over-refusal (PR 2).
- No change to the default provider (`mock` stays default for offline/CI).
- No new endpoints; no `.env.example` change (no new Settings field); no retrieval/generation/model change.

## Git / workflow
- Branch `feat/provider-visibility` (off `main`). Commit order: this plan -> backend (items 1-2) -> frontend
  (item 3) -> tests (item 4) -> docs + DONE markers (item 5); `pytest` + `npm test` green; push + PR.

## Files touched
- Backend: `app/api/schemas.py`, `app/api/routes.py`, `Makefile`, `tests/test_api.py`.
- Frontend: `frontend/src/api/types.ts`, `frontend/src/components/HealthDot.tsx`, `frontend/src/__tests__/*`.
- Docs: `README.md`, `docs/experiments/2026-06-18_provider-visibility-plan.md`. No new dependency.
