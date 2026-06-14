**Date:** 2026-06-13
**Topic:** V1 Phase 5 - grounded `/ask` (first serving endpoint + first LLM call)
**Motivation:** Implements the grounded-answering contract and refusal behavior from note 01 §5 and
the structured grounded synthesis from note 03/04 §6. Turns the Phase 4b retrieval output
(`retrieve_with_parents` -> scored chunks + parent context + `sufficient_context` gate) into a
cited answer via `POST /ask`, or the exact refusal string when context is insufficient. No baseline
eval run id exists yet; this endpoint is what the Phase 7 eval harness will measure.
**Hypothesis:** A scope-required `/ask` returns a structured, context-only cited answer when the
Retrieval Gate passes and the exact refusal string (without calling the LLM) when it fails,
verifiable fully offline with a deterministic MockLLM and overridden retrieval.
**Preconditions:** Phases 1-4b merged to `main` (`retrieve_with_parents`, `RetrievalResult`,
`ParentSection`, `Chunk` exist); `.venv` installed; clean working tree on branch `feat/v1-phase5-ask`
(branched off `main`, since Phase 4b PR #6 is merged).

Confirmed: Anthropic Claude via the official `anthropic` SDK behind an `LLMClient` abstraction; model
`claude-opus-4-8` (configurable); native structured output (`messages.parse`) if the installed SDK
exposes it, else JSON-schema/tool output + Pydantic validation. Scope guardrails: generation core +
`/ask` only. NO checklist/email/`/detect-missing` (Phase 6), NO eval harness (Phase 7), NO auth, NO
streaming, NO real Anthropic calls in tests. `/ask` requires `university_slug`; answers use retrieved
context only; on insufficient context, return the exact refusal string.

## 1) Deps, config, .env.example (+ verify SDK structured-output API)
- **Goal:** Add the Anthropic dep and typed LLM config; confirm the structured-output mechanism.
- **Files:** `requirements.txt`, `app/core/config.py`, `.env.example`.
- **Steps:**
  - Add `anthropic` to `requirements.txt` (pin to installed major).
  - After install, verify `Anthropic(api_key="x").messages.parse` exists (no network); record the
    chosen mechanism (parse vs json_schema/tool + `model_validate`).
  - Add `llm_provider` (`anthropic`|`mock`, default `anthropic`), `anthropic_model`
    (`claude-opus-4-8`), `anthropic_api_key: str | None = None`, `llm_max_tokens: int = 4096`.
  - Document `LLM_PROVIDER`, `ANTHROPIC_MODEL`, `LLM_MAX_TOKENS`, `ANTHROPIC_API_KEY` in `.env.example`.
- **Test / verification:** `pip install -r requirements.txt`; existing suite green; every Settings field documented.
- **Expected outcome:** Typed, documented LLM config; structured-output mechanism chosen and recorded.
- **DONE (commit `168a53d`):** Added `anthropic` (0.109.1) to requirements (pinned `>=0.109,<1.0`);
  verified `messages.parse(output_format=...)` IS available -> using native structured outputs
  (parsed object on `block.parsed_output`). Added `llm_provider`/`anthropic_model`
  (`claude-opus-4-8`)/`anthropic_api_key`/`llm_max_tokens` to `Settings`; documented all four in `.env.example`.

## 2) Generation core (app/rag/generation.py)
- **Goal:** Provider-agnostic grounded generation with an offline-testable mock.
- **Files:** `app/rag/generation.py` (new).
- **Steps:**
  - `Citation(source_id, heading_path)`; `GroundedAnswer(answer, citations, insufficient_context,
    confidence)`; `REFUSAL_MESSAGE = "Information not found in the official documents."`; `DISCLAIMER`.
  - `LLMClient` Protocol `generate(*, system, user, output_model) -> T`; `MockLLMClient(response)`;
    `AnthropicLLMClient(model, api_key, max_tokens)` (lazy import; verified structured-output path);
    `get_llm_client(settings)` factory.
  - `build_grounded_prompt(question, parents)`: six-point contract (context-only; prefer primary over
    secondary authority; state conflicts; exact refusal string; no inference; structured output);
    user message embeds parents labeled with source_id/heading_path/source_authority.
  - `generate_grounded_answer(question, retrieval_result, *, llm_client)`: gate-false -> refusal
    `GroundedAnswer` without an LLM call; gate-true -> prompt + `llm_client.generate`, then drop
    citations whose `source_id` is absent from the retrieved context.
- **Test / verification:** see item 4.
- **Expected outcome:** Deterministic refusal + grounded synthesis behind an abstraction.
- **DONE (commit `168a53d`):** Added `app/rag/generation.py` with the contracts, `REFUSAL_MESSAGE`
  + `DISCLAIMER`, `LLMClient` protocol, `MockLLMClient`, `AnthropicLLMClient` (lazy, `messages.parse`),
  `get_llm_client`, `build_grounded_prompt` (six-point contract), and `generate_grounded_answer`
  (gate refusal without an LLM call + citation grounding guard).

## 3) /ask endpoint (app/api/schemas.py, app/api/routes.py)
- **Goal:** Thin `POST /ask` wiring retrieval + generation.
- **Files:** `app/api/schemas.py`, `app/api/routes.py`.
- **Steps:**
  - `AskRequest(question, university_slug, programme_slug=None)` (question/university_slug non-empty);
    `AskResponse(answer, citations, insufficient_context, confidence, university_slug, programme_slug,
    disclaimer)`.
  - `POST /ask`: dependencies `provide_llm_client` + `provide_retriever` (callable bound to settings);
    route runs retriever -> `generate_grounded_answer` -> maps to `AskResponse` (+ `DISCLAIMER`). No
    provider/LLM logic in the route.
- **Test / verification:** see item 4.
- **Expected outcome:** Working grounded endpoint; `app/api` stays thin.
- **DONE (commit `168a53d`):** Added `AskRequest`/`AskResponse` to `schemas.py` and a thin `POST /ask`
  to `routes.py` wiring `provide_retriever` + `provide_llm_client` dependencies (overridable);
  maps `GroundedAnswer` + request scope + `DISCLAIMER` to `AskResponse`. `university_slug` required.

## 4) Tests (offline; MockLLM)
- **Goal:** Prove refusal + grounded answer + validation offline.
- **Files:** `tests/test_generation.py`, `tests/test_ask_endpoint.py` (new).
- **Steps:**
  - `test_generation.py`: insufficient -> exact `REFUSAL_MESSAGE`, no LLM call; sufficient -> MockLLM
    answer; citations outside the context dropped; prompt includes parent text + refusal instruction.
  - `test_ask_endpoint.py` (`TestClient` + `dependency_overrides`): override retriever (sufficient) +
    MockLLM -> 200 answer + citations + disclaimer; override retriever (insufficient) -> refusal string
    + `insufficient_context=True`, LLM not called; missing `university_slug` / empty question -> 422.
- **Test / verification:** `pytest` all green, fully offline, prior tests untouched.
- **Expected outcome:** Green suite; refusal/answer/validation/grounding covered.
- **DONE (commit `168a53d`):** Added `tests/test_generation.py` (refusal-without-LLM, grounded answer,
  hallucinated-citation drop, prompt contents) and `tests/test_ask_endpoint.py` (`TestClient` +
  `dependency_overrides`: 200 grounded answer, refusal path, 422 missing university_slug / empty question).
  - Metric / result: `pytest` -> 69 passed (61 prior + 8 new), fully offline.
  - Decision: Phase 5 complete; `/ask` is the first grounded endpoint. Phase 6 (checklist/email)
    reuses this `LLMClient` + structured-output pattern.
