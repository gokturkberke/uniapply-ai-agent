**Date:** 2026-06-14
**Topic:** qwen3:1.7b stability across repeated serial local smoke runs (+ proposed temperature/seed pinning)
**Motivation:** The model-comparison smoke (`2026-06-14_local-model-comparison-smoke-plan.md`, Item 4)
found that small local models (1.7b-3b) are **stochastically unreliable** on grounded probes - they
intermittently set `insufficient_context=true` on clearly-groundable questions even though retrieval
returns the exact supporting chunk. That plan recorded two suspected causes as follow-ups: (1) sampling is
**unpinned** (no `temperature`/`seed` sent), and (2) `LLM_MAX_TOKENS=768` truncation. The baseline
`qwen3:1.7b` was only run 1-2x on the uni-assist probe, so its recorded pass may be a lucky draw. Before
expanding the corpus, we need to know whether the current laptop-safe default is actually **stable**.
**Hypothesis (measurable):** Across **N=5** serial runs of each probe with `qwen3:1.7b` +
`LLM_MAX_TOKENS=768`, the two grounded probes return `insufficient_context=false` with the correct
in-scope citation in **5/5** runs and the refusal probe returns the exact refusal in **5/5** runs
(= "stable"). If any grounded probe is **< 5/5** (= "flaky"), then pinning `temperature=0` + `seed=42`
raises both grounded probes to 5/5.
**Preconditions:** V1 + V1.1 merged to `main`; `qwen3:1.7b` is the laptop-safe default; the CS mini-corpus
index exists locally (`data/index/qdrant`, gitignored); Ollama installed; **inspection confirms the
`local_openai` client currently sends only `model`, `max_tokens`, `messages` - no `temperature`/`seed`**
(generation.py:159-166), and `config.py` has no `local_llm_temperature`/`local_llm_seed`.

This plan is **mostly docs/measurement**. The only possible code is the **conditional** Phase B
implementation (typed sampling settings + payload wiring + tests), which is **proposed here and NOT coded
until explicitly approved**, and only if Phase A shows flakiness.

## Design summary
- **Phase A (measurement, no code):** repeat the existing 3 `/ask` probes N=5 serially on `qwen3:1.7b`
  under current (unpinned) sampling; record a per-run matrix; classify stable vs flaky.
- **Phase B (conditional):** only if Phase A is flaky. **B1** is a minimal, additive implementation
  (typed `local_llm_temperature`/`local_llm_seed`, passed only in the local client payload, documented in
  `.env.example`, covered by `httpx.MockTransport` tests; Mock/Anthropic unchanged; default behavior
  unchanged unless the env vars are set). **B2** re-runs Phase A's N=5 with `temperature=0`, `seed=42`.
- **Methodology guardrails (lessons from the comparison slice):** serial requests only; run the API on a
  **dedicated port** (e.g. `:8011`, not `:8000`) to avoid colliding with any pre-existing uvicorn, and
  **verify the serving model with `ollama ps`** before trusting results; no committed reports/logs.

---

## 1) Inspect (confirm the sampling gap; no change)
- **Goal:** Confirm exactly what the local client sends today, so Phase B is correctly scoped.
- **Files:** read-only: `app/rag/generation.py`, `app/core/config.py`, `.env.example`,
  `docs/experiments/local-llm-smoke.md`, `2026-06-14_local-model-comparison-smoke-plan.md`.
- **Findings:**
  - `LocalOpenAICompatibleLLMClient.generate` posts to `/chat/completions` a body of only `model`,
    `max_tokens`, `messages` (generation.py:159-166). **No `temperature`, no `seed`, no `options`** ->
    sampling is unpinned (Ollama uses its model default, typically non-zero temperature).
  - `__init__` (127-140) and the `get_llm_client` `local_openai` branch (201-207) carry no sampling args.
  - `config.py` exposes `local_llm_base_url`/`local_llm_model`/`local_llm_api_key`/`llm_max_tokens` only -
    no `local_llm_temperature`/`local_llm_seed`.
  - Ollama's OpenAI-compatible endpoint accepts **top-level** `temperature` and `seed` (not the native
    `options` object), so Phase B would add them as top-level body fields.
- **Test / verification:** findings recorded here; no behavior change.
- **Expected outcome:** confirms Phase A needs no code, and Phase B is a small additive change.
- **DONE (commit `707ab0d`):** Confirmed the local client sends only `model`/`max_tokens`/`messages`
  (no `temperature`/`seed`); constructor and `get_llm_client` carry no sampling args; `config.py` has no
  sampling fields. Phase A needs no code; Phase B (if reached) is a small additive change adding top-level
  OpenAI-compatible `temperature`/`seed`.

## 2) Phase A - current-behavior stability smoke (qwen3:1.7b, N=5, no code)
- **Goal:** Quantify `qwen3:1.7b` stability under current unpinned sampling.
- **Files:** none (run-only); results recorded into this item's DONE marker + the matrix below.
- **Steps:**
  - `ollama ps`/`ollama list` confirm `qwen3:1.7b` is available; start the API on a dedicated port,
    **no `--reload`**: `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 uvicorn
    app.main:app --port 8011`; verify via `ollama ps` that `qwen3:1.7b` is the model serving requests.
  - Run **serially, one at a time** (never parallel), **N=5 each**, reusing
    `docs/experiments/local-llm-smoke.md` (scope `university-of-konstanz` /
    `msc-computer-and-information-science`):
    1. Konstanz eligibility / points-system grounded question.
    2. uni-assist timing grounded question.
    3. Harvard MBA tuition unsupported (refusal) question.
- **Capture per run:** `latency_sec` (`curl -w`), HTTP status, `insufficient_context`, citation
  `source_id` correctness, refusal correctness, schema-valid / safe-refusal behavior, any observable
  malformed-JSON/schema failure, any Ollama 500 / timeout, and subjective fan/heat notes.
- **Observability note:** a grounded refusal and a parse-failure fallback produce the **same** response
  shape (`insufficient_context=true`, `citations=[]`, `confidence=0.0`); without product instrumentation
  (out of scope here) we cannot separate "model judged insufficient" from "unparseable JSON -> safe
  fallback". We record the count and infer "generation-side over-refusal" (retrieval is independently
  confirmed sufficient in the comparison slice).
- **Classification:** **stable** = both grounded probes 5/5 (`insufficient_context=false` + correct
  in-scope citation) and refusal 5/5 exact; **flaky** = any grounded probe < 5/5.
- **Test / verification:** matrix filled; stable/flaky classification stated.
- **Expected outcome:** a definitive stability read for the current default; drives the decision and
  whether Phase B is needed.
- **DONE (recorded):** Ran on a dedicated `:8011` instance (no `--reload`), model verified
  `qwen3:1.7b` via `ollama ps` (~1.9 GB, 100% GPU). N=5 serial per probe, all HTTP 200, no Ollama
  500/timeout, no observable malformed JSON:
  - Probe 1 (eligibility/points): **5/5 grounded**, citation `konstanz-cis-official-programme-page`,
    latency ~4.9-9.1 s (cold first run ~9 s).
  - Probe 2 (uni-assist timing): **4/5 grounded** (citation `uni-assist-processing-time-konstanz-cis`),
    **1/5 over-refused** (run5: `insufficient_context=true`, `citations=[]`), latency ~4.0-5.1 s.
  - Probe 3 (Harvard MBA): **5/5 exact refusal** (`insufficient_context=true`, `citations=[]`),
    latency ~3.5-6.4 s.
  - **Classification: FLAKY** (probe 2 is 4/5, < 5/5). Better than `qwen2.5:3b` (1/5) and `llama3.2:3b`
    (3/5) from the comparison slice, but not deterministic. The lone over-refusal is generation-side
    (retrieval was independently confirmed sufficient for this query in the comparison slice). Per the
    decision rule this points to Phase B; **PAUSED for explicit confirmation before any Phase B code.**

## 3) Phase B1 - PROPOSED deterministic-sampling implementation (conditional; do NOT code until approved)
- **Goal:** Allow pinning local sampling so a deterministic smoke is possible - **only if Phase A is
  flaky**, and only after explicit approval of this implementation.
- **Files (when approved):** `app/core/config.py`, `app/rag/generation.py`, `.env.example`,
  `tests/test_local_llm.py` (extend).
- **Proposed steps (not executed in this slice):**
  - `config.py`: add `local_llm_temperature: float | None = None` and `local_llm_seed: int | None = None`
    (both default `None` = unset = current behavior).
  - `LocalOpenAICompatibleLLMClient.__init__`: accept `temperature: float | None = None`,
    `seed: int | None = None`; in `generate`, include them in the request body **only when not None**
    (use `is not None`, NOT truthiness - `temperature=0.0` is falsy but valid). Add as **top-level**
    OpenAI-compatible fields. `get_llm_client` passes the two new settings through.
  - `.env.example`: document `LOCAL_LLM_TEMPERATURE` and `LOCAL_LLM_SEED` (unset by default; note
    `temperature=0` + `seed=42` for a deterministic local smoke).
  - Tests (`httpx.MockTransport`, offline): (a) when both are set, the captured request body includes
    `temperature` and `seed` with those values; (b) when unset (default), the body contains **neither**
    key (proves default behavior unchanged); (c) `temperature=0.0` is included (guards the truthiness
    bug). Mock and Anthropic clients and their tests unchanged.
- **Constraints:** additive only; no change to retrieval/endpoints/schemas/artifacts; Mock + Anthropic
  paths untouched; default behavior identical unless the env vars are set; no new dependency.
- **Test / verification:** `pytest` green (existing 111 + new payload tests).
- **DONE / DROPPED:**

## 4) Phase B2 - deterministic N=5 re-run (conditional; after B1 lands)
- **Goal:** Re-measure stability with pinned sampling and compare to Phase A.
- **Files:** none (run-only); results recorded into this item's DONE marker + the matrix.
- **Steps (only if Phase A flaky AND B1 approved+landed):** restart the API on `:8011` with the same env
  plus `LOCAL_LLM_TEMPERATURE=0 LOCAL_LLM_SEED=42`; verify the body now carries them; re-run the same 3
  probes N=5 serially; fill the matrix; compare grounded-consistency vs Phase A.
- **Test / verification:** matrix filled; A-vs-B consistency delta stated.
- **Expected outcome:** either 5/5 grounded (deterministic smoke recommended) or still flaky.
- **DONE / DROPPED:**

## 5) Decision + record (docs-only)
- **Goal:** Record the stability read and the decision; change no product default.
- **Decision rule:**
  - **Phase A stable** -> keep `qwen3:1.7b` default; skip Phase B; next work is corpus expansion
    (separate approved plan).
  - **Phase A flaky but B (temperature=0/seed=42) stabilizes it** (5/5 grounded) -> document the
    deterministic local smoke (`LOCAL_LLM_TEMPERATURE=0 LOCAL_LLM_SEED=42`) as the **recommended** way to
    run the local smoke; `qwen3:1.7b` stays the default.
  - **Still flaky after B** -> keep `qwen3:1.7b` as a **laptop-safe demo only**; do **not** rely on local
    models for any quality baseline; record that conclusion.
- **Files:** this plan (DONE markers + matrix); optionally a one-line pointer in
  `docs/experiments/local-llm-smoke.md` if a deterministic smoke is recommended.
- **Test / verification:** decision captured; default unchanged in this slice.
- **DONE / DROPPED:**

## Stability matrix (filled during execution; shape-level evidence only)
| phase | probe | grounded/refused count (of 5) | citation source_id | refusal exact | latency range (s) | JSON/500/timeout | fan/heat | notes |
|---|---|---|---|---|---|---|---|---|
| A (unpinned) | eligibility/points | grounded 5/5 | konstanz-cis-official-programme-page | - | ~4.9-9.1 | all 200, no 500/timeout | light (inferred) | stable on this probe |
| A (unpinned) | uni-assist timing | grounded 4/5, refused 1/5 | uni-assist-processing-time-konstanz-cis (4/5) | - | ~4.0-5.1 | all 200, no 500/timeout | light (inferred) | run5 over-refused -> FLAKY |
| A (unpinned) | Harvard MBA refusal | refused 5/5 | - | yes 5/5 | ~3.5-6.4 | all 200, no 500/timeout | light (inferred) | exact refusal every run |
| B (temp0/seed42) | eligibility/points | | | - | | | | only if Phase A flaky + B1 approved |
| B (temp0/seed42) | uni-assist timing | | | - | | | | only if Phase A flaky + B1 approved |
| B (temp0/seed42) | Harvard MBA refusal | | - | | | | | only if Phase A flaky + B1 approved |

## Non-goals
- Keep `qwen3:1.7b` as the default; **no config default change** to the model.
- No corpus changes / no corpus expansion in this slice; no retrieval/endpoint/schema/artifact changes.
- No full eval/judge baseline (`scripts.evaluate`); no model comparison; no new dependencies.
- No parallel local requests (a parallel request previously caused an Ollama 500).
- **Never committed:** `data/`, `.env`, Ollama model files, generated reports under
  `docs/experiments/runs/`, or logs containing large source text / full answers.
- Phase B1 code is **not** written until explicitly approved, and only if Phase A is flaky.

## Caveats
- A smoke is not a quality baseline; it measures stability of grounded-or-refuse shape, not answer quality.
- Sampling is currently stochastic (unpinned); N=5 is a small sample - it characterizes, it does not prove.
- First `/ask` is cold (model load); record cold vs warm roughly.
- `LLM_MAX_TOKENS=768` truncation may still contribute to over-refusal even with pinned sampling; if Phase
  B is inconclusive, a `LLM_MAX_TOKENS=1024` retest is a separate follow-up (not in this slice).

## Git / workflow (explicit order)
- Start from updated `main`; branch: **`docs/local-llm-determinism-smoke`**.
- **Wait for explicit approval before any code, config, or smoke execution.**
- Commit order: (1) **this plan file first, only after approval**; (2) run Phase A and commit its recorded
  results (DONE marker + matrix); (3) **pause and explicitly reconfirm** - even if Phase A is flaky, I do
  NOT write any Phase B code until you give a separate explicit go-ahead; once confirmed, B1 lands as its
  own commit with `pytest` green and B2 runs after; (4) push the branch and open a PR to `main`. **Never
  push `main`.**

## Files touched
- `docs/experiments/2026-06-14_local-llm-determinism-smoke-plan.md` (this plan; committed first after approval).
- Conditional (Phase B1 only, if approved): `app/core/config.py`, `app/rag/generation.py`, `.env.example`,
  `tests/test_local_llm.py`. No corpus/retrieval/endpoint/schema/artifact change; Mock + Anthropic preserved.
