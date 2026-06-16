**Date:** 2026-06-16
**Topic:** Drop the Anthropic provider (local/mock only) + fix `docker-test` (tests not in image)
**Motivation:** Running the Docker milestone surfaced two issues: (1) `make docker-test` collects 0 tests
because the `Dockerfile` does not copy `tests/`; (2) `/ask` returns 500 because the default
`LLM_PROVIDER=anthropic` has no key. The project is local-first (Ollama) with no Anthropic key, so the
decision is to **remove Anthropic entirely** and **default to `mock`** - which also removes the cause of
the `/ask` 500. This finishes the Docker milestone on the same branch (`infra/dockerized-backend`, PR open).
**Hypothesis:** With Anthropic removed and the default provider `mock`, `pytest` stays green, `/ask` works
out-of-box (mock grounded answer, no 500), `docker-test` runs the full suite, and `local_openai` + `mock`
behavior is unchanged. No new dependency; grounding-or-refuse + scoping guarantees intact.
**Preconditions:** on `infra/dockerized-backend` (Docker files merged-pending); `pytest` currently 117 green.

---

## 1) Fix `docker-test` (Dockerfile copies tests)
- **Files:** `Dockerfile`.
- **Steps:** add `COPY tests/ ./tests/` (after the `scripts/` copy) so `pytest` finds the suite in the
  container. `tests/fixtures/` comes along.
- **Test / verification:** (user-run) `make docker-test` -> 117 passed.
- **DONE / DROPPED:**

## 2) Remove the Anthropic provider (code + dependency)
- **Files:** `app/rag/generation.py`, `app/core/config.py`, `requirements.txt`.
- **Steps:**
  - `generation.py`: delete `AnthropicLLMClient` (class + the lazy `import anthropic`), remove the
    `anthropic` branch in `get_llm_client`, and update the module docstring (drop the Anthropic sentences).
    Keep `LLMClient` Protocol, `MockLLMClient`, `LocalOpenAICompatibleLLMClient`, `safe_generate`, etc.
  - `config.py`: remove `anthropic_model` and `anthropic_api_key`; change
    `llm_provider: Literal["anthropic","mock","local_openai"] = "anthropic"` to
    `Literal["mock","local_openai"] = "mock"`. Keep `llm_max_tokens` (used by the local client). Update the
    stale `ANTHROPIC_API_KEY` docstring comment.
  - `requirements.txt`: remove the `anthropic>=0.109,<1.0` line.
- **Test / verification:** `pytest` green; `get_llm_client(Settings())` returns `MockLLMClient` by default.
- **DONE / DROPPED:**

## 3) `.env.example`
- **Files:** `.env.example`.
- **Steps:** remove `ANTHROPIC_MODEL`, `ANTHROPIC_API_KEY`, and the Anthropic comment lines; set
  `LLM_PROVIDER=mock`; update the provider comment block to list only `mock` and `local_openai`. Keep
  `LLM_MAX_TOKENS` and the `LOCAL_LLM_*` block.
- **Test / verification:** `docker compose config` parses with `LLM_PROVIDER: mock`.
- **DONE / DROPPED:**

## 4) Tests
- **Files:** `tests/test_local_llm.py` (+ grep for any other reference).
- **Steps:** drop the `AnthropicLLMClient` import and rewrite `test_get_llm_client_mock_and_anthropic_unaffected`
  to assert only `mock` -> `MockLLMClient` and `local_openai` -> `LocalOpenAICompatibleLLMClient` (no
  Anthropic). Confirm no other test imports/refers to Anthropic.
- **Test / verification:** `pytest` green and fully offline.
- **DONE / DROPPED:**

## 5) Docs (factual mentions only; no rule changes)
- **Files:** `README.md`, `docs/docker.md`, `CLAUDE.md`, `AGENTS.md`, `scripts/evaluate.py` (docstring).
- **Steps:** update provider lists from "Mock/Anthropic/local-OpenAI" to "Mock/local-OpenAI (Ollama)";
  remove Anthropic-key instructions; in CLAUDE.md/AGENTS.md update the status sentence + the stale
  "ANTHROPIC_API_KEY ... commented placeholder / not wired up" note to reflect Anthropic is removed. Rules untouched.
- **Test / verification:** no remaining `anthropic` references outside historical `docs/experiments/` plans.
- **DONE / DROPPED:**

## 6) Verify
- **Steps:** `pytest` (local) green; `docker compose config` shows `LLM_PROVIDER: mock`; (user-run, daemon)
  `make docker-up` + `make docker-test` (117) + `/ask` scoped -> mock grounded answer (no 500) and an
  out-of-scope question -> exact refusal.
- **DONE / DROPPED:**

## Non-goals
- No change to `local_openai` or `mock` behavior, retrieval, corpus, endpoints, schemas, or the
  grounding-or-refuse guarantee. No new dependency. Re-adding Anthropic later is a fresh provider if ever needed.

## Git / workflow
- Continue on `infra/dockerized-backend` (finishes the Docker milestone; PR not yet merged). Commits:
  docker-test fix; Anthropic removal (code+deps); `.env.example` + tests; docs; DONE markers. `pytest`
  green before push. Never push `main`.
