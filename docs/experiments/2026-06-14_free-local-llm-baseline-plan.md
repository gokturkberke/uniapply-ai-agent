**Date:** 2026-06-14
**Topic:** V1.1 - free/local LLM provider (OpenAI-compatible: Ollama / LM Studio) for a real-ish baseline
**Motivation:** The CS mini-corpus baseline landed (PR #10): verified 6-source registry, ingest/chunk/
index + mock smoke passed, pytest 99. The real Anthropic baseline was deferred (no `ANTHROPIC_API_KEY`).
To produce a real-ish baseline run without paid API access, add a free **local OpenAI-compatible**
provider while preserving MockLLM (CI/offline), keeping Anthropic optional, and holding the
grounded-or-refuse + cited + no-fabricated-facts guarantees.
**Hypothesis:** A `LocalOpenAICompatibleLLMClient` using the already-present `httpx`, plus a JSON
extraction + Pydantic validation layer and a conservative safe-fallback, can satisfy the generic
`LLMClient.generate(output_model=...)` contract for every existing schema (GroundedAnswer, Checklist,
MissingDocsResult, EmailDraft, FaithfulnessVerdict) with no new dependency and no change to the
MockLLM/Anthropic paths.
**Preconditions:** V1 + CS mini-corpus merged to `main`; 99 tests green; `httpx>=0.27` already a dependency.

This is a **new V1.1 follow-up plan**. It is additive and does **not** modify the completed CS
mini-corpus baseline plan (`docs/experiments/2026-06-13_*`), which remains historically correct as merged.

## Design summary
- **Reuse `httpx`** (no new dep): POST to `{LOCAL_LLM_BASE_URL}/chat/completions` (OpenAI-compatible;
  Ollama `:11434/v1`, LM Studio `:1234/v1`), `Authorization: Bearer {api_key}`, generous timeout.
- **Structured output via prompt + extraction (not strict mode):** augment the system prompt with
  `output_model.model_json_schema()` + "return ONLY one JSON object"; extract JSON (tolerate ```json
  fences / small surrounding prose), then `output_model.model_validate_json(...)`. Generic over `output_model`.
- **Fail safely** (see Item 3 for the exact contract): the local client converts its own failures to
  `LLMOutputError`; `safe_generate` catches only that and returns the caller's refusal/conservative shape.

---

## 1) Inspect (confirm seams; no new dependency)
- **Goal:** Confirm the integration seams and that no new dependency is required, before designing.
- **Files:** read-only: `app/rag/generation.py`, `app/core/config.py`, `requirements.txt`, `.env.example`, tests.
- **Findings:**
  - `httpx>=0.27,<1.0` is already a dependency (TestClient) -> no new dependency for an OpenAI-compatible client.
  - Single seam: `LLMClient.generate(*, system, user, output_model: type[T]) -> T`; `get_llm_client`
    selects by `settings.llm_provider` (`Literal["anthropic","mock"]`).
  - Call sites: `generate_grounded_answer` (generation.py), `generate_checklist` /
    `detect_missing_documents` / `draft_email` (artifacts.py), `judge_faithfulness` (evaluation.py).
  - Existing safe shapes: `_refusal_answer()` (generation), `_checklist_refusal` / `_missing_refusal` /
    `_email_refusal` (artifacts). `AnthropicLLMClient.generate` raises `ValueError` on no-parsed-output.
- **Test / verification:** findings recorded here; no behavior change.
- **DONE / DROPPED:**

## 2) Config (`app/core/config.py`, `.env.example`)
- **Goal:** Configure the local provider; no secrets, no new deps.
- **Files:** `app/core/config.py`, `.env.example`.
- **Steps:** `llm_provider: Literal["anthropic", "mock", "local_openai"]`; add
  `local_llm_base_url: str = "http://localhost:11434/v1"`, `local_llm_model: str = "qwen3:4b"`,
  `local_llm_api_key: str = "ollama"`; reuse `llm_max_tokens`. Document `LLM_PROVIDER` (3 options),
  `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_API_KEY` in `.env.example` with Ollama + LM Studio notes.
- **DONE / DROPPED:**

## 3) Local provider + safe fallback (`app/rag/generation.py`; wire call sites)
- **Goal:** OpenAI-compatible client behind the generic seam, with an explicit, narrow error model.
- **Files:** `app/rag/generation.py` (+ `artifacts.py`, `evaluation.py` call sites).
- **Error-handling contract (explicit):**
  - **Only** `LocalOpenAICompatibleLLMClient.generate` raises `LLMOutputError`, and **only** for these,
    converting them to `LLMOutputError`: non-2xx HTTP / connection error; missing or wrong-shaped
    `choices[0].message.content`; JSON not extractable / not decodable; Pydantic `ValidationError`.
    Any other (unexpected) exception is NOT converted -> it propagates.
  - `safe_generate(llm_client, *, system, user, output_model, fallback)` catches **only**
    `LLMOutputError` and returns `fallback`. Every other exception propagates unchanged.
  - `MockLLMClient` and `AnthropicLLMClient` are **not modified**, never raise `LLMOutputError`, and their
    unexpected errors are **never hidden** by `safe_generate` (e.g. Anthropic's `ValueError` still propagates).
- **Steps:** add `LLMOutputError(Exception)` and `_extract_json(text) -> str`; add
  `LocalOpenAICompatibleLLMClient(*, base_url, model, api_key, max_tokens, http_client=None)` (lazy
  `httpx.Client` or injected for tests); add `safe_generate`; add the `local_openai` branch to
  `get_llm_client`; route the five call sites through `safe_generate` with their existing refusal shapes
  (judge fallback = `FaithfulnessVerdict(supported=False, reasoning="conservative fallback: unparseable judge output")`).
- **DONE / DROPPED:**

## 4) Tests (`tests/test_local_llm.py`, new; offline via `httpx.MockTransport`)
- **Goal:** Prove the provider, extraction, and safe fallback with no running server.
- **Steps (cases):**
  - **Happy path:** MockTransport returns `{"choices":[{"message":{"content": <valid JSON>}}]}` ->
    `generate` parses + Pydantic-validates -> correct model.
  - **Tolerance:** content wrapped in a ```json fence``` and/or small extra prose -> extracted + validated.
  - **Failures -> `LLMOutputError` -> safe behavior:** malformed response shape (no `choices`/`content`);
    invalid JSON; valid JSON but schema-invalid (missing required field). Then `safe_generate` -> fallback;
    `generate_grounded_answer` (local client yielding bad output) -> refusal; judge -> `supported=False`.
  - **Selection:** `get_llm_client("local_openai")` -> `LocalOpenAICompatibleLLMClient`.
  - **Unaffected paths:** `get_llm_client("mock"|"anthropic")` still return their types; the existing
    full suite passes unchanged (Mock + Anthropic behavior preserved).
- **DONE / DROPPED:**

## 5) Docs: `.env.example` local baseline + gold-set summary
- **Goal:** Make the local baseline runnable from docs; publish a fact-free gold-set summary.
- **Files:** `.env.example` (item 2), `docs/experiments/eval-goldset-summary.md` (new, committed).
- **Steps:** the summary contains **only** counts, categories, scopes (university_slug / programme_slug),
  referenced `source_id`s, and notes. It contains **no question answers and no admission facts**
  (deadlines, fees, requirements, etc.). The gold set itself (`data/eval/gold.jsonl`) stays gitignored.
- **DONE / DROPPED:**

## 6) Verify + conditional local baseline run
- **Goal:** Green tests are a hard gate; a real-ish baseline only if a local server is available.
- **Steps:**
  - **`pytest` is a mandatory gate** - it must pass (prior 99 + new local tests, all offline) before any run.
  - Check for a reachable local server (e.g. `curl -s localhost:11434/api/tags`). **If not reachable:
    STOP - do not run the baseline**; record the exact manual command in this item's DONE marker.
  - **If reachable:** run
    `LLM_PROVIDER=local_openai LOCAL_LLM_BASE_URL=http://localhost:11434/v1 LOCAL_LLM_MODEL=qwen3:4b LOCAL_LLM_API_KEY=ollama python -m scripts.evaluate --run-label cs-mini-corpus-local-qwen3-4b-baseline`.
    The report writes to `docs/experiments/runs/cs-mini-corpus-local-qwen3-4b-baseline/report.json`,
    which is **gitignored and NOT committed** (summarize numbers in the DONE marker instead).
- **DONE / DROPPED:**

## Notes / caveats (stated explicitly)
- **Mock smoke is not a quality baseline** - it only proves pipeline wiring; real metrics need a real LLM.
- **`country_scope=["all"]` in the CS corpus is temporary** scaffolding, not final country-aware retrieval.
- **FastEmbed mean-pooling warning** is noted but intentionally NOT acted on in this plan.

## Non-goals
- No shared/global source mechanism (would need its own approved plan).
- No `retrieval_min_score` tuning; no hybrid search / reranking.
- Do NOT remove Anthropic; do NOT break MockLLM; do NOT require Ollama/LM Studio in `pytest`.
- Do NOT fabricate admission facts.

## Git / workflow (explicit order)
- Branch: **`feat/v1.1-local-llm-provider`**.
- Commit order: (1) **this plan file first**; (2) then implementation + tests + docs commit(s); fill each
  item's DONE marker with its commit hash; (3) `pytest` green; (4) **push + open a PR to `main`** (never push `main`).
- **Never committed:** `data/` (raw/normalized/chunks/index/eval), `.env`, any API key, and generated
  reports under `docs/experiments/runs/`.

## Files touched
- `app/core/config.py`, `app/rag/generation.py`, `app/rag/artifacts.py`, `app/rag/evaluation.py`,
  `.env.example`, `tests/test_local_llm.py` (new), `docs/experiments/eval-goldset-summary.md` (new),
  this plan file. No new dependency; Anthropic + MockLLM preserved.
