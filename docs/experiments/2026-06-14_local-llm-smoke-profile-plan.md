**Date:** 2026-06-14
**Topic:** Lightweight, laptop-safe local-LLM smoke/demo profile (not a quality baseline)
**Motivation:** The V1.1 `local_openai` provider was merged and verified live with `qwen3:4b` via
Ollama (health OK; grounded `/ask` with citations; one broad question correctly refused via the model
choosing `insufficient_context=true`; retrieval not broken; one parallel local request caused an
Ollama-side HTTP 500 while serial requests worked). But `qwen3:4b` is too heavy for this MacBook:
~2.5 GB download, ~3.3 GB memory during inference, ~55-75 s per answer, noticeable fan/heat. We need a
small profile to demo/smoke the app without heating the laptop and without the full eval harness.
**Hypothesis:** Switching to a smaller local model (`qwen3:1.7b`) with a lower generation budget
(`LLM_MAX_TOKENS=768`), exercised with 2-3 **serial** smoke probes (no judge/eval harness, no parallel
requests), preserves the grounded-or-refuse + cited behavior end to end with materially lower
memory/latency/heat - achievable with **no new dependency** and **no change** to retrieval, corpus,
registry, endpoints, schemas, or artifact behavior (Anthropic + Mock providers untouched).
**Preconditions:** V1.1 `local_openai` provider merged to `main`; the offline test suite is green
(111 tests at the V1.1 merge); the CS mini-corpus index exists locally (`data/index/qdrant`,
gitignored); Ollama installed locally.

This is a **new, small follow-up plan**. It is additive and does **not** modify the completed CS
mini-corpus plan (`2026-06-14_computer-science-mini-corpus-baseline-plan.md`) or the V1.1 free/local
provider plan (`2026-06-14_free-local-llm-baseline-plan.md`); both remain historically correct.

## Design summary
- **Env-only knobs already exist** (Inspect, Item 1): `LOCAL_LLM_MODEL` and `LLM_MAX_TOKENS` are already
  typed `Settings` fields read from the environment, and the local client already forwards `max_tokens`
  in the `/chat/completions` body. So the smaller model + lower budget need **no code** - only a default
  flip + documentation.
- **Smoke = documented serial curl probes** against a running `uvicorn` + Ollama: one `/health` GET and
  three `/ask` POSTs, run **one at a time** (a parallel local request already triggered an Ollama 500).
  No eval/judge harness, no `scripts.evaluate`, no committed report.
- **Recommended demo model `qwen3:1.7b`** (laptop-safe default); `qwen3:4b` documented as the optional
  higher-quality choice; `gemma3:1b` as a smaller fallback; `llama3.2:3b` as an optional comparison.
- **A JSON/schema-validation failure is a smoke RESULT, not a product bug**: the provider already falls
  back to a safe grounded refusal on unparseable output (`safe_generate` -> `_refusal_answer()`), so a
  smaller model that emits malformed JSON simply yields a refusal, which we record as an observation.

---

## 1) Inspect (confirm env knobs + smoke surface; no new dependency)
- **Goal:** Confirm the smaller model + lower token budget need no code, and pin the exact smoke surface.
- **Files:** read-only: `app/core/config.py`, `app/rag/generation.py`, `app/api/routes.py`,
  `app/api/schemas.py`, `.env.example`, `data/registry/sources.json`.
- **Findings:**
  - `llm_max_tokens: int = 4096` (`config.py:45`) is read from `LLM_MAX_TOKENS`, and
    `LocalOpenAICompatibleLLMClient.generate` already sends `max_tokens` in the request body
    (`generation.py:161`) -> `LLM_MAX_TOKENS=768` works today, no code change.
  - `local_llm_model: str = "qwen3:4b"` (`config.py:48`) is read from `LOCAL_LLM_MODEL` -> switching the
    demo model is env-only; an optional one-line default flip makes the laptop-safe model the default.
  - Smoke surface: `GET /health`; `POST /ask` with body `{question, university_slug, programme_slug?}`
    (`schemas.py:18-27`). Response carries `answer`, `citations`, `insufficient_context`, `confidence`.
  - Real committed scopes/source_ids (for probe targeting, not for asserting facts):
    `university-of-konstanz` / `msc-computer-and-information-science`
    (`konstanz-cis-official-programme-page`, `uni-assist-vpd-konstanz-cis`,
    `uni-assist-processing-time-konstanz-cis`) and `paderborn-university` / `msc-computer-science`
    (the parallel three).
  - No test asserts the `local_llm_model` default string (`tests/test_local_llm.py` constructs the
    client with an explicit model and only isinstance-checks selection) -> flipping the default is safe.
- **Test / verification:** findings recorded here; no behavior change.
- **Expected outcome:** confirms this is a default-flip + docs slice; nothing in retrieval/endpoints/
  artifacts/providers needs to move.
- **DONE (commit `86283ee`):** Confirmed `LLM_MAX_TOKENS` and `LOCAL_LLM_MODEL` are already env-readable
  `Settings` fields (the local client already forwards `max_tokens`), pinned the `/health` + `/ask` smoke
  surface and the real Konstanz/Paderborn scopes/source_ids, and confirmed no test asserts the
  `local_llm_model` default string. No behavior change; this is a default-flip + docs slice.

## 2) Config default + `.env.example` (recommend the lightweight demo model)
- **Goal:** Make `qwen3:1.7b` the recommended laptop-safe local default while keeping `qwen3:4b`
  available as the optional higher-quality choice.
- **Files:** `app/core/config.py` (one line: `local_llm_model` default), `.env.example`
  (`LOCAL_LLM_MODEL` value + the local-provider comment block).
- **Steps:**
  - Flip `local_llm_model` default from `"qwen3:4b"` to `"qwen3:1.7b"` (one line; no other config change).
    `LOCAL_LLM_MODEL` stays env-overridable, so the only effect is that the default local profile is
    laptop-safe; `qwen3:4b` remains documented as the optional higher-quality model.
  - In `.env.example`: set `LOCAL_LLM_MODEL=qwen3:1.7b`; in the comment block, recommend `qwen3:1.7b` for
    low-resource local demos, note `qwen3:4b` as optional higher-quality, `gemma3:1b` as a smaller
    fallback, and `llama3.2:3b` as an optional comparison; add a line recommending `LLM_MAX_TOKENS=768`
    (raise to `1024` if a model truncates its JSON) for local smoke/demo. No new variables.
- **Test / verification:** `pytest` stays green (no model-string assertions); a one-line check that
  `Settings(llm_provider="local_openai").local_llm_model == "qwen3:1.7b"`.
- **Expected outcome:** the out-of-the-box local profile is laptop-safe; `qwen3:4b` remains a documented opt-in.
- **DONE (commit `5049841`):** Flipped `local_llm_model` default to `"qwen3:1.7b"` (`config.py`); updated
  `.env.example` to `LOCAL_LLM_MODEL=qwen3:1.7b` with the model recommendations (qwen3:1.7b default,
  qwen3:4b optional, gemma3:1b fallback, llama3.2:3b comparison) and the `LLM_MAX_TOKENS=768` demo-budget
  note. `pytest` -> 111 passed (no model-string assertions);
  `Settings(llm_provider="local_openai").local_llm_model == "qwen3:1.7b"` confirmed.

## 3) Docs: `docs/experiments/local-llm-smoke.md` (exact serial commands)
- **Goal:** A short, copy-pasteable runbook for a laptop-safe smoke/demo, with no eval harness.
- **Files:** `docs/experiments/local-llm-smoke.md` (new, committed).
- **Steps (content):**
  - **Setup:** `ollama serve`; `ollama pull qwen3:1.7b` (fallback `gemma3:1b`; optional `llama3.2:3b`).
  - **Run the API with the demo profile (one terminal):**
    `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 uvicorn app.main:app`
  - **Four serial probes (run one at a time; never fire them in parallel).** All `/ask` probes use scope
    `university-of-konstanz` / `msc-computer-and-information-science`. Probes 2-3 are the two
    **live-verified grounded questions**; probe 4 is the refusal probe:
    1. **Health:** `curl -s localhost:8000/health` -> expect `status: ok`.
    2. **Grounded `/ask` (eligibility / points system):** "Does the University of Konstanz admission
       committee decide eligibility using the application documents and a points system?"
    3. **Grounded `/ask` (uni-assist timing):** "How early does uni-assist recommend applying before the
       deadline?"
    4. **Unsupported / refusal `/ask`:** "What is the tuition fee for an MBA at Harvard Business School?"
  - **Assertion contract (shape only, never the answer text - except the refusal string):**
    - Probes 2-3 (grounded): assert HTTP 200, `insufficient_context == false`, `len(citations) >= 1`, and
      the cited `source_id` is in the Konstanz scope (probe 2 likely `konstanz-cis-official-programme-page`;
      probe 3 likely `uni-assist-processing-time-konstanz-cis`). The `answer` text is **optionally printed
      for human inspection only** - it is **not** asserted as a fact.
    - Probe 4 (refusal): assert HTTP 200, `answer == "Information not found in the official documents."`
      (the **only** hard text assertion), `insufficient_context == true`, `citations == []`.
  - Each probe uses `curl -w "\n time_total=%{time_total}s\n"` so latency is captured **roughly**
    (note the first `/ask` is cold: it includes model load; later calls are warm). Do not optimize.
  - **Explicit notes in the doc:** (a) grounded smoke probes assert **response shape only**, not answer
    text; only the refusal string is asserted verbatim; probes are kept separate from the gitignored gold
    set (eval-set isolation) and assert **no admission facts**; (b) a JSON/schema-validation failure (incl.
    `LLM_MAX_TOKENS` truncation) yields a **safe refusal** and is recorded as a **smoke result, not a
    product bug** - raising `LLM_MAX_TOKENS` to `1024` is the knob; (c) keep requests serial - a parallel
    local request already produced an Ollama 500.
- **Test / verification:** doc is fact-free and self-consistent with the real scopes/source_ids from Item 1.
- **Expected outcome:** anyone can run a laptop-safe smoke in minutes without the eval harness.
- **DONE (commit `5049841`):** Added `docs/experiments/local-llm-smoke.md`: prerequisites, `ollama pull
  qwen3:1.7b`, the `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 uvicorn` run
  line, four serial probes (health + 2 live-verified grounded `/ask` + 1 refusal) with rough latency
  capture, and the shape-only assertion contract (verbatim only for the refusal string). Serial-only and
  truncation-is-a-smoke-result notes included; no admission facts asserted.

## 4) Verify + conditional smoke run
- **Goal:** Green tests are a hard gate; a real serial smoke only if Ollama + a small model are available.
- **Steps:**
  - **`pytest` is a mandatory gate** - the full offline suite must pass before/after the doc + default flip.
  - Check for a reachable local server (`curl -s localhost:11434/api/tags`) and a pulled small model.
    **If not reachable / not pulled: STOP** - do not run the smoke; record the exact manual commands from
    Item 3 in this item's DONE marker.
  - **If reachable:** start the API with the demo profile and run the four serial probes; record, in this
    DONE marker, rough latency per probe (cold vs warm) and a per-probe pass/fail (health ok / grounded+cited
    / grounded+cited / refused) - **no admission facts, no gold-set questions, no committed report**.
- **Test / verification:** `pytest` green; smoke outcomes summarized in the DONE marker only.
- **Expected outcome:** a recorded, reproducible laptop-safe smoke result (or the exact command to run it later).
- **DONE (commit `5049841`):** `pytest` -> 111 passed (mandatory gate met). Smoke run was deferred at
  implementation time (no local server reachable); the user later ran it on the merged code (below).
- **Smoke run (recorded post-merge):** model `qwen3:1.7b`, `LLM_MAX_TOKENS=768`, serial, against the local
  CS index (`data/index/qdrant`, gitignored). All four probes **passed**:
  - Probe 1 health: ok, `time_total` ~0.010 s.
  - Probe 2 (eligibility / points system): `insufficient_context=false`, citation `source_id`
    `konstanz-cis-official-programme-page`, ~7.53 s (cold; includes model load).
  - Probe 3 (uni-assist timing): `insufficient_context=false`, citation `source_id`
    `uni-assist-processing-time-konstanz-cis`, ~4.67 s; warm re-run ~4.51 s.
  - Probe 4 (Harvard MBA tuition): `answer` exactly "Information not found in the official documents.",
    `insufficient_context=true`, `citations=[]`, ~6.55 s.
  - Latency: ~4.5-7.5 s per answer serial, vs the earlier `qwen3:4b` run at ~55-75 s with noticeable
    fan/heat - `qwen3:1.7b` is materially more laptop-safe, confirming the hypothesis. No report committed.
  - Observation (not a blocker, out of scope here): citation `source_id`s are correct, but `heading_path`
    sometimes arrives as a single string containing `">"` rather than a list of separate components.
    Grounding is `source_id`-based so this does not affect the smoke; it is a candidate future
    citation-polish item (would need its own plan; no product code changed here).

## Non-goals
- Do NOT run the full 12-question eval/judge baseline (`scripts.evaluate`) in this slice.
- Do NOT change retrieval, corpus, registry, endpoints, schemas, or artifact behavior.
- Do NOT remove or alter the Anthropic or Mock providers; keep the `local_openai` provider as-is.
- No new dependencies; no `retrieval_min_score` calibration (separate future work).
- No new smoke script in this slice - the smoke is documented serial curl commands (simplest, no new
  test surface, naturally serial). (If a tiny testable serial-probe script is wanted, it needs its own item.)
- No parallel local LLM requests (a parallel request already caused an Ollama 500).
- Do NOT fabricate admission facts; smoke probes are generic and assert none.

## Caveats (stated explicitly)
- A smoke is **not** a quality baseline - it proves the small model runs end to end, not answer quality.
- The first `/ask` is cold (model load) and slower; warm calls are faster. Record both roughly.
- Too-low `LLM_MAX_TOKENS` can truncate the JSON -> safe refusal; raise to `1024` if so (a smoke result).
- Model footprints other than the user-observed `qwen3:4b` numbers are **not pre-asserted** here; they
  are measured/observed during the smoke.

## Git / workflow (explicit order)
- Branch: **`feat/v1.1-local-llm-smoke-profile`**.
- Commit order: (1) **this plan file first**; (2) config default flip + `.env.example` + the smoke doc
  commit, filling each item's DONE marker with its commit hash; (3) `pytest` green; (4) **push + open a PR
  to `main`** (never push `main`).
- **Never committed:** `data/` (raw/normalized/chunks/index/eval), `.env`, any API key, Ollama models, and
  any generated report under `docs/experiments/runs/`.

## Files touched
- `docs/experiments/2026-06-14_local-llm-smoke-profile-plan.md` (this plan; committed first).
- `docs/experiments/local-llm-smoke.md` (new runbook; committed).
- `app/core/config.py` (one line: `local_llm_model` default).
- `.env.example` (`LOCAL_LLM_MODEL` value + comment block).
- No new dependency; Anthropic + Mock + retrieval + endpoints + schemas + artifacts unchanged.
