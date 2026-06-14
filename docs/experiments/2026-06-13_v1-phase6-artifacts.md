**Date:** 2026-06-13
**Topic:** V1 Phase 6 - artifact generation (/checklist, /detect-missing, /draft-email)
**Motivation:** Completes the V1 product surface from note 03 §1 "V1 Core Capabilities" by adding the
three remaining artifact endpoints on top of the Phase 5 grounded-generation pattern
(scope-required retrieval -> Retrieval Gate -> structured LLM output -> refuse-or-answer with the
citation grounding guard). No baseline eval run id exists yet; these endpoints plus `/ask` are what
the Phase 7 eval harness will measure.
**Hypothesis:** The three artifacts (checklist, missing-document detection, source-anchored email)
reuse the Phase 5 grounded structured-output + refusal pattern with new Pydantic schemas, verifiable
fully offline with a deterministic MockLLM.
**Preconditions:** Phase 5 merged to `main` (`LLMClient`/`generate(output_model=...)`, `MockLLMClient`,
`generate_grounded_answer`, `retrieve_with_parents`, and the `provide_retriever`/`provide_llm_client`
route deps all exist); `.venv` installed; clean working tree on branch `feat/v1-phase6-artifacts`.

Confirmed: all three endpoints in one PR. Scope guardrails: every endpoint requires `university_slug`;
`/checklist` and `/detect-missing` also require `programme_slug`; `/draft-email` keeps it optional.
Grounding-or-refuse everywhere (refuse without an LLM call when context is insufficient; citations
validated against retrieved context; no fabricated facts). app/api stays thin; tests offline (MockLLM);
NO agent/intent routing, NO auth, NO streaming, NO eval harness (Phase 7), NO new deps/config.

## 1) Extract shared helpers (app/rag/generation.py)
- **Goal:** Reuse Phase 5 internals across artifacts without duplication; `/ask` behavior unchanged.
- **Files:** `app/rag/generation.py`.
- **Steps:** extract `format_context(retrieval_result) -> str` (parent-context block builder, from
  inside `build_grounded_prompt`) and `ground_citations(citations, retrieval_result) -> list[Citation]`
  (source-id filter, from inside `generate_grounded_answer`); have both existing functions call them.
- **Test / verification:** existing `/ask` + generation tests stay green (no behavior change).
- **Expected outcome:** Shared, reusable helpers; identical `/ask` behavior.
- **DONE (commit `b2ced02`):** Extracted `format_context`, `is_groundable`, and `ground_citations`
  in `generation.py`; refactored `build_grounded_prompt` + `generate_grounded_answer` to use them.
  `/ask` + generation tests unchanged/green.

## 2) Artifact schemas + services (app/rag/artifacts.py)
- **Goal:** Grounded, cited structured outputs for the three artifacts, behind the Phase 5 pattern.
- **Files:** `app/rag/artifacts.py` (new).
- **Steps:**
  - Schemas: `ChecklistItem(requirement, detail)`, `Checklist(items, citations, insufficient_context)`;
    `MissingDocsResult(missing, satisfied, citations, insufficient_context)`;
    `EmailDraft(subject, body, citations, insufficient_context)` (reuse `Citation`).
  - `generate_checklist(retrieval_result, *, llm_client)`,
    `detect_missing_documents(profile, retrieval_result, *, llm_client)`,
    `draft_email(topic, retrieval_result, *, llm_client)` — each: refuse (no LLM) when
    `not sufficient_context or not parents`; grounded prompt via `format_context`; `generate`;
    normalize model-`insufficient_context` to the schema refusal; `ground_citations`.
  - Module constant for the canned requirements retrieval query.
- **Test / verification:** see item 4.
- **Expected outcome:** Three service functions producing grounded artifacts or refusals.
- **DONE (commit `b2ced02`):** Added `app/rag/artifacts.py` with the three schemas and
  `generate_checklist` / `detect_missing_documents` / `draft_email` (refuse without LLM when not
  groundable; normalize model-insufficient to refusal; `ground_citations`). `REQUIREMENTS_QUERY` constant.

## 3) Endpoints (app/api/schemas.py, app/api/routes.py)
- **Goal:** Thin `POST /checklist`, `/detect-missing`, `/draft-email` wiring retrieval + services.
- **Files:** `app/api/schemas.py`, `app/api/routes.py`.
- **Steps:**
  - Requests: `ChecklistRequest(university_slug, programme_slug)`,
    `DetectMissingRequest(university_slug, programme_slug, profile: list[str])`,
    `EmailRequest(university_slug, programme_slug=None, topic)`; matching responses (payload + scope
    + `disclaimer`).
  - Routes call the injected retriever (canned requirements query for checklist/detect-missing,
    `topic` for email) scoped by university/programme, then the matching service, then map to the
    response + `DISCLAIMER`. Reuse `provide_retriever` + `provide_llm_client`.
- **Test / verification:** see item 4.
- **Expected outcome:** Three grounded endpoints; `app/api` thin.
- **DONE (commit `b2ced02`):** Added the three request/response schema pairs and thin `POST /checklist`,
  `/detect-missing`, `/draft-email` routes reusing `provide_retriever` + `provide_llm_client`;
  checklist/detect-missing require `programme_slug`, email optional. Route fn `draft_email_endpoint`
  avoids shadowing the imported `draft_email`.

## 4) Tests (offline; MockLLM)
- **Goal:** Prove refusal + grounded payload + validation offline for all three.
- **Files:** `tests/test_artifacts.py`, `tests/test_artifact_endpoints.py` (new).
- **Steps:**
  - `test_artifacts.py`: each service refuses (no LLM call) when insufficient / no parents; returns the
    MockLLM payload when sufficient; drops out-of-context citations; normalizes model-insufficient to refusal.
  - `test_artifact_endpoints.py` (`TestClient` + `dependency_overrides`): 200 payload + disclaimer when
    sufficient; refusal shape when insufficient (LLM not called); missing `programme_slug` /
    empty required fields -> 422.
- **Test / verification:** `pytest` all green, fully offline, prior tests untouched.
- **Expected outcome:** Green suite; refusal/payload/validation/grounding covered for all three.
- **DONE (commit `b2ced02`):** Added `tests/test_artifacts.py` (service refusal/payload/grounding/
  normalization) and `tests/test_artifact_endpoints.py` (`TestClient` + overrides: 200 payload,
  refusal without LLM, 422 missing programme_slug / topic).
  - Metric / result: `pytest` -> 87 passed (71 prior + 16 new), fully offline.
  - Decision: Phase 6 complete; V1 product surface done (Q&A + checklist + detect-missing + email).
    Phase 7 (eval harness) is next.
