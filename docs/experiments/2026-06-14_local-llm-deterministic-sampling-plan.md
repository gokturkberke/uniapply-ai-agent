**Date:** 2026-06-14
**Topic:** Deterministic local sampling for the `local_openai` provider (opt-in `temperature`/`seed`) + deterministic smoke re-run (Phase B)
**Motivation:** Phase A (`2026-06-14_local-llm-determinism-smoke-plan.md`, Item 2) found `qwen3:1.7b`
**flaky** across N=5 serial smoke runs (eligibility 5/5, uni-assist timing **4/5**, Harvard refusal 5/5)
under **unpinned** sampling - the local client sends no `temperature`/`seed` (generation.py:159-166), so
Ollama uses a non-zero default temperature. The repo's reproducibility rule (CLAUDE.md section 5) also
wants stochastic operations pinned. This slice adds **opt-in** deterministic sampling and re-measures.
**Hypothesis (measurable):** Adding top-level OpenAI-compatible `temperature`/`seed` to the local request
payload and running `qwen3:1.7b` with `LOCAL_LLM_TEMPERATURE=0` + `LOCAL_LLM_SEED=42` raises the
uni-assist-timing probe from 4/5 to **5/5** (all three probes 5/5 across N=5), while the **default
(env unset) behavior is provably unchanged** (payload omits both keys).
**Preconditions:** V1 + V1.1 merged; **the Phase A PR (`docs/local-llm-determinism-smoke`) is merged** and
this slice starts from updated `main`; `qwen3:1.7b` is the default; the CS index exists locally
(`data/index/qdrant`, gitignored); Ollama installed; inspection confirms the local client has no sampling
params today.

This is the Phase B code slice split out from the Phase A determinism smoke (per request), on its own
branch `feat/local-llm-deterministic-sampling`. It is **additive and opt-in**: Mock and Anthropic are
untouched, and the model default is not changed.

## Design summary
- **Opt-in, default-off:** new typed settings `local_llm_temperature: float | None = None` and
  `local_llm_seed: int | None = None`. When `None` (default), the request payload is byte-for-byte the
  current one - no behavior change.
- **Top-level OpenAI-compatible fields:** when set, include `temperature` and `seed` at the top level of
  the `/chat/completions` body (Ollama's OpenAI-compatible endpoint reads them there, not in `options`).
- **Inclusion guard:** include each field **only when `is not None`** - NOT truthiness, because
  `temperature=0.0` is falsy but is the value we actually want for determinism.
- **Scope:** only `LocalOpenAICompatibleLLMClient` + its wiring + `.env.example` + tests change. No
  retrieval/corpus/endpoint/schema/artifact changes; no new dependency.

---

## 1) Inspect (re-confirm exact insertion points; no change)
- **Goal:** Pin the precise lines to touch so the change stays minimal.
- **Files:** read-only: `app/core/config.py`, `app/rag/generation.py`, `tests/test_local_llm.py`, `.env.example`.
- **Findings (from Phase A, to re-confirm at execution):**
  - `config.py`: `local_llm_*` block holds `base_url`/`model`/`api_key`; add the two sampling fields here.
  - `generation.py`: `LocalOpenAICompatibleLLMClient.__init__` (params) and `generate` (the `json={...}`
    body with `model`/`max_tokens`/`messages`); `get_llm_client` `local_openai` branch passes settings.
  - `tests/test_local_llm.py`: `_local_client` helper builds the client over `httpx.MockTransport`; its
    handler currently ignores the request - a capturing handler is needed to assert the request body.
- **Test / verification:** findings recorded; no behavior change.
- **DONE / DROPPED:**

## 2) Config + `.env.example` (typed settings; opt-in)
- **Goal:** Expose the two settings without changing default behavior.
- **Files:** `app/core/config.py`, `.env.example`.
- **Steps:**
  - `config.py`: add `local_llm_temperature: float | None = None` and `local_llm_seed: int | None = None`
    in the `local_llm_*` block.
  - `.env.example`: document them. **Recommended form: commented-out** so "unset" stays the default and
    startup never breaks:
    ```
    # Deterministic local smoke (optional; unset by default). Uncomment BOTH to enable:
    # LOCAL_LLM_TEMPERATURE=0
    # LOCAL_LLM_SEED=42
    ```
    Rationale / deviation from the literal request: writing `LOCAL_LLM_TEMPERATURE=` (empty) risks a
    startup `ValidationError`, since an empty string is not a valid `float`/`int` and is not `None`
    (unlike `ANTHROPIC_API_KEY=`, which is a valid empty `str`). The commented form documents the same
    two variables and the `0`/`42` recommendation without that footgun. (Implementation will confirm the
    empty-string parse behavior; if it does coerce to `None`, the literal form is harmless either way.)
- **Test / verification:** `pytest` green; `Settings()` defaults `local_llm_temperature is None` and
  `local_llm_seed is None`.
- **DONE / DROPPED:**

## 3) Provider wiring (`app/rag/generation.py`)
- **Goal:** Pass the settings into the request payload, opt-in, top-level, with the `is not None` guard.
- **Files:** `app/rag/generation.py`.
- **Steps:**
  - `LocalOpenAICompatibleLLMClient.__init__`: add `temperature: float | None = None`,
    `seed: int | None = None`; store them.
  - `generate`: build the base body (`model`/`max_tokens`/`messages`), then **add** `"temperature"` and
    `"seed"` to the body **only when the stored value `is not None`** (top-level keys). Everything else
    (schema-in-prompt, JSON extraction, `LLMOutputError` handling) is unchanged.
  - `get_llm_client` `local_openai` branch: pass `temperature=settings.local_llm_temperature`,
    `seed=settings.local_llm_seed`.
  - `MockLLMClient` and `AnthropicLLMClient` are **not modified**.
- **Test / verification:** covered by Item 4; existing suite stays green.
- **DONE / DROPPED:**

## 4) Tests (`tests/test_local_llm.py`, extend; offline `httpx.MockTransport`)
- **Goal:** Prove the payload includes/omits the fields correctly, with no running server.
- **Steps (cases):**
  - Add a **capturing** MockTransport handler that records the request body, then assert:
    a) `temperature` and `seed` set (e.g. `0.5`, `42`) -> request JSON contains both with those values;
    b) both unset (default `None`) -> request JSON contains **neither** key (default behavior unchanged);
    c) `temperature=0.0` set -> request JSON contains `"temperature": 0.0` (guards the truthiness bug).
  - Keep all existing local/mock/anthropic tests passing unchanged (Mock + Anthropic behavior preserved).
- **Test / verification:** `pytest` green (existing 111 + the new payload tests).
- **DONE / DROPPED:**

## 5) Phase B2 - deterministic N=5 re-run (after code + pytest green)
- **Goal:** Re-measure `qwen3:1.7b` stability with pinned sampling; compare to Phase A.
- **Files:** none (run-only); results recorded into this item's DONE marker + the matrix below.
- **Steps:**
  - Start the API on a **dedicated port** (e.g. `:8021`), **no `--reload`**:
    `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 LOCAL_LLM_TEMPERATURE=0
    LOCAL_LLM_SEED=42 uvicorn app.main:app --port 8021`; verify `qwen3:1.7b` is serving via `ollama ps`.
  - Run the same 3 probes (eligibility/points; uni-assist timing; Harvard MBA refusal), scope
    `university-of-konstanz` / `msc-computer-and-information-science`, **N=5 each, serial** (never parallel).
  - Capture per run: `latency_sec`, HTTP status, `insufficient_context`, citation `source_id`,
    refusal correctness, any Ollama 500/timeout, fan/heat notes.
- **Comparison target (Phase A):** eligibility **5/5**, uni-assist timing **4/5**, Harvard refusal **5/5**.
- **Test / verification:** matrix filled; A-vs-B consistency delta stated.
- **DONE / DROPPED:**

## 6) Decision + record
- **Goal:** Record the deterministic-smoke decision without changing the model default.
- **Decision rule:**
  - **B2 is 5/5 on all three probes** -> document the deterministic local smoke
    (`LOCAL_LLM_TEMPERATURE=0 LOCAL_LLM_SEED=42`) as the **recommended** way to run the local smoke (add a
    note to `docs/experiments/local-llm-smoke.md` and the `.env.example` comment).
  - **Still flaky after B2** -> keep `qwen3:1.7b` as a **laptop-safe demo only**; do **not** rely on local
    models for any quality baseline; record `LLM_MAX_TOKENS=1024` as a separate follow-up to try next.
  - **Either way: do NOT change the default model.**
- **Files:** this plan (DONE markers + matrix); `docs/experiments/local-llm-smoke.md` + `.env.example`
  note **only if** the deterministic smoke is recommended.
- **Test / verification:** decision captured; default unchanged.
- **DONE / DROPPED:**

## B2 matrix (filled during execution; shape-level evidence only)
| run config | probe | grounded/refused (of 5) | citation source_id | refusal exact | latency range (s) | 500/timeout | notes |
|---|---|---|---|---|---|---|---|
| temp0/seed42 | eligibility/points | | | - | | | vs Phase A 5/5 |
| temp0/seed42 | uni-assist timing | | | - | | | vs Phase A 4/5 (key probe) |
| temp0/seed42 | Harvard MBA refusal | | - | | | | vs Phase A 5/5 |

## Non-goals
- Do NOT change the default model (`qwen3:1.7b` stays the default); the two settings stay **unset by
  default** (behavior unchanged unless env vars are set).
- No retrieval/corpus/registry/endpoint/schema/artifact changes; no full eval/judge baseline; no model
  comparison; no new dependencies.
- No `LLM_MAX_TOKENS` change in this slice (1024 is a separate follow-up if B2 is still flaky).
- No parallel local requests (a parallel request previously caused an Ollama 500).
- **Never committed:** `data/`, `.env`, Ollama model files, generated reports under
  `docs/experiments/runs/`, or logs with large source text / full answers.

## Caveats
- At `temperature=0` Ollama decodes greedily, so output should already be deterministic from temperature
  alone; `seed=42` is belt-and-suspenders (and matters if a future run uses `temperature>0`).
- Residual nondeterminism is still possible (GPU float reductions, or `LLM_MAX_TOKENS=768` truncation
  intermittently tripping the safe-refusal fallback). If B2 is still flaky, that points to the
  `LLM_MAX_TOKENS=1024` follow-up, not to this payload change.
- N=5 characterizes, it does not prove; the smoke remains a wiring/stability check, not a quality baseline.

## Git / workflow (explicit order)
- **Start from updated `main` after the Phase A PR merges.** Branch: **`feat/local-llm-deterministic-sampling`**.
- Commit order: (1) **this plan file first**; (2) code (config + provider + `.env.example` + tests) as one
  commit with `pytest` green; (3) run B2 and commit the recorded matrix/decision; (4) push the branch and
  open a PR to `main`. **Never push `main`.**

## Files touched
- `docs/experiments/2026-06-14_local-llm-deterministic-sampling-plan.md` (this plan; committed first).
- `app/core/config.py`, `app/rag/generation.py`, `.env.example`, `tests/test_local_llm.py`.
- Conditional (only if B2 5/5): `docs/experiments/local-llm-smoke.md` + `.env.example` note. No
  corpus/retrieval/endpoint/schema/artifact change; Mock + Anthropic preserved; no new dependency.
