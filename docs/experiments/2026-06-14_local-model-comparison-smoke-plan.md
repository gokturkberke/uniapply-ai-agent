**Date:** 2026-06-14
**Topic:** Local model comparison smoke - one slightly smarter local model vs the qwen3:1.7b baseline (docs-only)
**Motivation:** `qwen3:1.7b` is the laptop-safe local default (V1.1) and its serial smoke is already
recorded as the baseline in `2026-06-14_local-llm-smoke-profile-plan.md` (Item 4): health ~0.010 s;
Konstanz eligibility/points-system grounded + cite `konstanz-cis-official-programme-page` ~7.53 s cold;
uni-assist timing grounded + cite `uni-assist-processing-time-konstanz-cis` ~4.67 s / ~4.51 s warm;
Harvard-MBA exact refusal ~6.55 s. `qwen3:4b` worked but was too heavy (~55-75 s/answer, fan/heat). We
want to check whether **one slightly smarter** local model improves structured-JSON / instruction
following while staying laptop-safe - without changing any product behavior.
**Hypothesis:** `qwen2.5:3b` passes all four serial smoke probes (health; two grounded `/ask` with
`insufficient_context=false` and a correct in-scope citation; one exact refusal) with reliable JSON/schema
behavior and acceptable latency/heat - materially lighter than `qwen3:4b`'s ~55-75 s - and therefore could
be recorded as an **optional smarter local model**, while `qwen3:1.7b` remains the default.
**Preconditions:** V1 + V1.1 merged to `main`; `qwen3:1.7b` is the laptop-safe default and its smoke is
already recorded (reused as baseline; no re-run required); the CS mini-corpus index exists locally
(`data/index/qdrant`, gitignored); Ollama installed.

This is a **docs-only experiment plan**. It changes **no product code, no config defaults, and no
retrieval/corpus/endpoint/schema/artifact behavior**. It reuses the existing smoke probes and assertion
contract from `docs/experiments/local-llm-smoke.md`.

## Design summary
- **Baseline = the recorded `qwen3:1.7b` smoke** (above). Do **not** re-run `qwen3:1.7b` unless we
  explicitly choose to re-verify.
- **Comparison mainly runs `qwen2.5:3b`** via the existing `local_openai` provider, env-only (no code, no
  config default change): `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen2.5:3b`.
- **Same four serial probes**, same shape-only grounded assertions and exact refusal assertion as the
  runbook. Serial only - a parallel local request previously caused an Ollama-side HTTP 500.
- **Record only shape-level evidence** (pass/fail, latency, citation `source_id`, refusal correctness,
  JSON/schema behavior, subjective fan/heat, short notes). No answer text, no retrieved source text, no
  committed data/reports/logs.

---

## 1) Baseline: reuse the recorded qwen3:1.7b smoke (no re-run)
- **Goal:** Fix the comparison reference without spending laptop cycles re-running the default.
- **Files:** read-only reference to `2026-06-14_local-llm-smoke-profile-plan.md` (Item 4) and
  `docs/experiments/local-llm-smoke.md`.
- **Steps:**
  - Use the already-recorded `qwen3:1.7b` numbers (Motivation) as the baseline row of the comparison table.
  - Do not re-run `qwen3:1.7b` unless we explicitly decide to re-verify (e.g. if results look suspicious).
- **Test / verification:** baseline row is copied verbatim from the recorded smoke; no new run.
- **Expected outcome:** a stable baseline row to compare `qwen2.5:3b` against.
- **DONE / DROPPED:**

## 2) Primary candidate: qwen2.5:3b serial smoke
- **Goal:** Measure whether `qwen2.5:3b` passes the same smoke with reliable JSON and acceptable load.
- **Rationale:** ~1.9 GB; expected better than `qwen3:1.7b` for structured JSON / instruction following,
  while in practice lighter than `qwen3:4b` (which was ~55-75 s/answer with fan/heat).
- **Files:** none (run-only); results recorded into this plan's DONE marker + the comparison table below.
- **Steps:**
  - `ollama pull qwen2.5:3b`.
  - Start the API **without `--reload`** (minimize extra load/noise):
    `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen2.5:3b LLM_MAX_TOKENS=768 uvicorn app.main:app`
  - Run the four probes **serially, one at a time** (never parallel), reusing
    `docs/experiments/local-llm-smoke.md`, each with `curl -w "... time_total=%{time_total}s"`:
    1. `GET /health`.
    2. Grounded - Konstanz eligibility / points-system question (scope `university-of-konstanz` /
       `msc-computer-and-information-science`).
    3. Grounded - uni-assist timing question (same scope).
    4. Refusal - Harvard MBA tuition question (same scope).
- **Assertion contract (unchanged from the runbook):**
  - Probes 2-3 (grounded): HTTP 200, `insufficient_context == false`, `len(citations) >= 1`, cited
    `source_id` in the expected Konstanz scope (probe 2 expected `konstanz-cis-official-programme-page`;
    probe 3 expected `uni-assist-processing-time-konstanz-cis`). **Do not hard-assert answer text.**
  - Probe 4 (refusal): HTTP 200, `answer == "Information not found in the official documents."`,
    `insufficient_context == true`, `citations == []`.
- **Test / verification:** capture per probe - pass/fail, `time_total` latency, actual citation
  `source_id`, refusal correctness, JSON/schema behavior (valid first-try vs malformed/truncated ->
  safe refusal), subjective fan/heat (acceptable or not), and short notes.
- **Expected outcome:** all four probes pass with correct in-scope citations and a correct refusal; JSON
  parses reliably; latency/heat clearly below the `qwen3:4b` experience.
- **DONE / DROPPED:**

## 3) Optional candidate: llama3.2:3b (conditional only)
- **Goal:** A fallback comparison **only if** `qwen2.5:3b` is inconclusive.
- **Trigger (run only if any holds for `qwen2.5:3b`):** inconclusive results; unreliable JSON/schema
  (repeated malformed output / forced refusals); or too slow / too hot.
- **Files:** none (run-only); results recorded as for Item 2.
- **Steps:** if triggered, `ollama pull llama3.2:3b` and repeat Item 2's procedure with
  `LOCAL_LLM_MODEL=llama3.2:3b` (same probes, same serial/assertion rules). **Do NOT test `qwen3:4b` or
  `gemma3:4b` in this slice.**
- **Test / verification:** same capture matrix as Item 2.
- **Expected outcome:** a tie-breaker row; if `qwen2.5:3b` already passed cleanly, this item is DROPPED.
- **DONE / DROPPED:**

## 4) Decision + record (docs-only)
- **Goal:** Record the comparison and the decision without changing any product/config.
- **Files:** this plan file (DONE markers + the comparison table); optionally a one-line pointer note in
  `docs/experiments/local-llm-smoke.md` (no behavior change).
- **Decision rule:**
  - `qwen3:1.7b` **stays the default** unless a separate, approved change says otherwise.
  - `qwen2.5:3b` may be recorded as an **"optional smarter local model"** only if it passes **all** probes,
    keeps citations correct and in-scope, refuses correctly, and latency/heat are acceptable. Otherwise it
    is noted as "not adopted" with the reason.
- **Test / verification:** decision and per-model results captured in the markers + table; no code/config change.
- **Expected outcome:** a clear, reproducible record; default unchanged in this slice.
- **DONE / DROPPED:**

## Comparison table (filled during execution; shape-level evidence only)
| model | probe | pass/fail | latency (s) | citation source_id | refusal correct | JSON/schema | fan/heat | notes |
|---|---|---|---|---|---|---|---|---|
| qwen3:1.7b (baseline) | health | pass | ~0.010 | - | - | - | acceptable | recorded baseline |
| qwen3:1.7b (baseline) | eligibility/points | pass | ~7.53 cold | konstanz-cis-official-programme-page | - | ok | acceptable | recorded baseline |
| qwen3:1.7b (baseline) | uni-assist timing | pass | ~4.67 / ~4.51 warm | uni-assist-processing-time-konstanz-cis | - | ok | acceptable | recorded baseline |
| qwen3:1.7b (baseline) | Harvard MBA refusal | pass | ~6.55 | - | yes | ok | acceptable | recorded baseline (citations=[]) |
| qwen2.5:3b | health | | | | | | | |
| qwen2.5:3b | eligibility/points | | | | | | | |
| qwen2.5:3b | uni-assist timing | | | | | | | |
| qwen2.5:3b | Harvard MBA refusal | | | | | | | |
| llama3.2:3b (optional) | ... | | | | | | | only if Item 3 triggered |

## Non-goals
- **Docs-only:** no product code changes, **no config default change** (`local_llm_model` stays
  `qwen3:1.7b`), no retrieval/corpus/registry/endpoint/schema/artifact changes.
- No full eval/judge baseline (`scripts.evaluate`); no new dependencies.
- Do NOT test `qwen3:4b` or `gemma3:4b` in this slice.
- No parallel local LLM requests (a parallel request previously caused an Ollama 500).
- **Never committed:** `data/` (raw/normalized/chunks/index/eval), `.env`, Ollama model files, generated
  reports under `docs/experiments/runs/`, or logs containing large source text / full answers.

## Caveats (stated explicitly)
- A smoke is **not** a quality baseline - it proves the model runs end to end with correct shape, not
  answer quality.
- First `/ask` is cold (model load) and slower; warm calls are faster. Record both roughly.
- Too-low `LLM_MAX_TOKENS` can truncate JSON -> the provider returns a **safe refusal**; that is a smoke
  result, not a bug. If a grounded probe refuses only due to truncation, raise `LLM_MAX_TOKENS` to `1024`
  and re-run that probe.
- Footprint figures (e.g. ~1.9 GB for `qwen2.5:3b`) are approximate and confirmed/observed during the run.

## Git / workflow (explicit order)
- Start from updated `main`; branch: **`docs/local-model-comparison-smoke`** (holds both the plan and the
  completed result note).
- Commit order: (1) **this plan file first** (now); (2) **after approval**, run the smoke and commit
  **only** the completed docs note/results (fill the DONE markers + comparison table with their commit
  hash); (3) push the branch and open a PR to `main`. **Never push `main`.**

## Files touched
- `docs/experiments/2026-06-14_local-model-comparison-smoke-plan.md` (this plan; committed first).
- Later (after the run): this plan's DONE markers + comparison table; optionally a one-line pointer in
  `docs/experiments/local-llm-smoke.md`. No product code, no config, no new dependency.
