**Date:** 2026-06-15
**Topic:** Stronger-answer-model comparison on the eval harness (qwen3:4b vs the qwen3:1.7b baseline)
**Motivation:** The quantitative baseline (`2026-06-15_cs-corpus-eval-baseline-plan.md`, run-label
`cs-corpus-expansion-local-qwen3-1.7b`) showed the pipeline is correct and safe - `retrieval_recall=0.923`,
`citation_grounding_rate=1.000`, **0 false answers** - but `refusal_accuracy=0.550`, dragged entirely by
**9 false refusals** (the small model over-refusing in-scope, well-supported facts; generation-side, since
retrieval and citation-grounding are fine). The open question: does a **stronger answer model** close that
false-refusal gap while preserving the safety property (no false answers / no blending)? The strongest
locally available model is `qwen3:4b` (already pulled; no API key needed).
**Hypothesis (measurable):** With `qwen3:4b` (deterministic `temp0`/`seed42`), `refusal_accuracy` rises
materially above the 0.550 baseline (it correctly answers a substantial share of the 9 baseline
false-refusal questions), while keeping **0 false answers** and `citation_grounding_rate=1.000`;
`retrieval_recall` is unchanged (model-independent). `faithfulness_rate` may stop being degenerate (now
self-judged by qwen3:4b) but remains a secondary, self-judged signal.
**Preconditions:** the eval-baseline slice merged to `main`; `qwen3:4b` pulled; Ollama up; the local index
+ 20-question gold set built (gitignored). This is a **deliberate one-off** heavy run - `qwen3:4b` was
~55-75 s/answer with fan/heat - so it is serial and not a default/demo change.

This is a **docs-only run-and-record slice**: no `app/` code, no corpus/gold/retrieval/endpoint/schema
changes, no new dependency, **no change to the default model** (`qwen3:1.7b` stays the laptop-safe default).
The generated `report.json` is gitignored; numbers are summarized in the DONE markers.

## Design summary
- Re-run the **same** harness + **same** 20-question gold set, changing only `LOCAL_LLM_MODEL` to
  `qwen3:4b` (deterministic sampling identical). `scripts.evaluate` wires one client to both answer and
  judge, so the judge also becomes `qwen3:4b` - still a self-judge, so `faithfulness_rate` stays a weak
  signal; the **decision rests on the answer-side, judge-independent metrics** (`refusal_accuracy`,
  `citation_recall`, with `retrieval_recall`/`citation_grounding_rate` as invariants).
- The comparison is **answer-model isolation**: `retrieval_recall` should be identical to the baseline
  (retrieval is model-independent); any movement in `refusal_accuracy`/`citation_recall` is attributable to
  the answer model.
- **Safety is a hard gate, not just a metric:** the 7 `should_refuse` questions must still all refuse. A
  stronger, less-conservative model could start answering an out-of-scope/cross-institution question - that
  would be a false answer / blend and is the most important thing to check.

---

## 1) Inspect (confirm comparison validity; no change)
- **Goal:** Confirm the only variable is the answer model and which metrics are answer-attributable.
- **Files:** read-only: `app/rag/evaluation.py`, `scripts/evaluate.py` (already mapped in the baseline slice).
- **Findings:** `retrieval_recall` is model-independent (must match baseline); `refusal_accuracy`,
  `citation_recall`, `citation_grounding_rate` come from the answer model; `faithfulness_rate` is the
  (self-)judge. Same gold set, same retrieval, same deterministic sampling -> a clean A/B on the answer model.
- **Test / verification:** findings recorded; no behavior change.
- **DONE (commit `f388da6`):** Confirmed the A/B is clean in principle (same gold/retrieval/sampling; only
  the answer model changes; `retrieval_recall` invariant; refusal/citation answer-side; faithfulness
  self-judged). Execution then surfaced a token-budget confound - see Item 2.

## 2) Run the qwen3:4b eval (deterministic; one-off, heavy)
- **Goal:** Produce the qwen3:4b metric table over the same 20-question gold set.
- **Files:** none (run-only); report gitignored, numbers go in the marker.
- **Steps:**
  - Confirm Ollama is up with `qwen3:4b` and the index/gold exist.
  - Run (serial, in-process; expect it to be slow and warm the laptop - a deliberate one-off):
    `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:4b LLM_MAX_TOKENS=768 LOCAL_LLM_TEMPERATURE=0
    LOCAL_LLM_SEED=42 python -m scripts.evaluate --run-label cs-corpus-expansion-local-qwen3-4b`
  - Capture the printed metric table + `by_category`, and the per-question breakdown from `report.json`.
- **Test / verification:** the run completes for all 20 questions; `report.json` written (gitignored).
- **Expected outcome:** `retrieval_recall` ~= 0.923 (invariant); `refusal_accuracy` > 0.550;
  `citation_grounding_rate` = 1.0; 0 false answers.
- **DONE (recorded; result is a CONFOUND, not a quality signal):** Ran qwen3:4b at `LLM_MAX_TOKENS=768`
  (run-label `cs-corpus-expansion-local-qwen3-4b`): `retrieval_recall=0.923`, but
  `refusal_accuracy=0.350`, `citation_recall=citation_grounding_rate=faithfulness_rate=0.000`,
  **0/13 in-scope answered** (the model refused all 20). **Root cause proven by direct probe:** at
  `max_tokens=768` qwen3:4b returns `finish_reason=length` with **empty message content** (its reasoning
  consumes the whole budget) -> `_extract_json` fails -> `safe_generate` falls back to the refusal. At
  `max_tokens=4096` the **same** prompt returns clean valid JSON (`{"answer":"Yes","citations":[konstanz
  -cis-official-programme-page],"insufficient_context":false,...}`, `finish_reason=stop`). So the 768 run
  measured **truncation**, not the model.

## 3) Compare vs the qwen3:1.7b baseline (per-metric + per-question)
- **Goal:** Quantify exactly what the stronger model changed, and confirm safety held.
- **Steps:**
  - Side-by-side metric table: qwen3:1.7b (0.923 / 0.875 / 1.000 / 0.550 / 0.000) vs qwen3:4b.
  - **False-refusal set (the 9):** for each baseline false-refusal id, record whether qwen3:4b now answers
    it correctly (with the expected in-scope citation) or still refuses.
  - **Safety gate (the 7 `should_refuse`):** confirm qwen3:4b still refuses all 7 - **any newly-answered
    one is a false answer / blend** and must be reported (with the cited sources) as the top finding.
  - Note `retrieval_recall` parity (sanity: model-independent) and any `faithfulness_rate` change (secondary).
- **Test / verification:** the false-refusal deltas and the 7-refusal safety check are both tabulated.
- **Expected outcome:** a clear answer to "does a stronger model close the gap, and at what
  safety/latency cost?"
- **DONE (recorded):** At 768: **0/9** baseline false-refusals recovered, 9/9 still refused, 0/13 in-scope
  answered. **Safety gate held: 0 false answers** (all 7 `should_refuse` refused). But the comparison is
  **invalid at 768** (qwen3:4b truncated to empty content). Cross-implication **tested with a control run**
  (qwen3:1.7b @4096, addendum below): it is **identical to @768 per-question** -> the qwen3:1.7b baseline
  is **budget-robust** and its 9 false-refusals are **genuine** small-model over-refusal, **NOT** a
  truncation artifact (this corrects my initial hypothesis that the baseline might also be truncated).
  Only qwen3:4b truncates at 768; its fair comparison still needs the heavy 4096 run.

## 4) Decision + record
- **Decision rule:**
  - **qwen3:4b materially raises `refusal_accuracy` AND keeps 0 false answers** -> record qwen3:4b as the
    recommended **optional quality** answer model (heavier; `qwen3:1.7b` stays the laptop-safe default).
  - **qwen3:4b introduces any false answer / blend** (answers a `should_refuse` question) -> highest-priority
    finding: a stronger, less-conservative model trades safety for recall; do **not** recommend it without a
    grounding/refusal-prompt hardening slice. Record the offending id(s) + citations.
  - **Only marginal gain** -> conclude local models cap here; recommend a **keyed Anthropic** answer+judge
    eval as the real quality reference (separate slice, needs a key).
  - The default model / corpus / gold are unchanged regardless.
- **Files:** this plan (DONE markers + comparison table). Report gitignored.
- **DONE (recorded):** **Comparison INCONCLUSIVE at `LLM_MAX_TOKENS=768`** - the run measured a token
  truncation confound (proven), not answer quality, so none of the decision-rule branches apply yet. Do
  NOT conclude qwen3:4b is more conservative; it grounds correctly at 4096. **Corrective next step:**
  re-run the eval at a higher budget (4096 confirmed sufficient for qwen3:4b) for **both** models -
  qwen3:1.7b (quick) and qwen3:4b (heavy) - to get the real comparison and a corrected baseline. The
  default model / corpus / gold are unchanged. New general finding: **`LLM_MAX_TOKENS=768` is too low for
  qwen3-family models that emit reasoning tokens** (content truncates to empty -> safe-refusal fallback);
  this affects any eval/smoke at that budget. Re-run is gated on the heavy qwen3:4b cost (user decision).

## Comparison table (filled at execution; numbers only, no admission facts)
qwen3:4b column is at `LLM_MAX_TOKENS=768` and is a **truncation artifact** (empty content ->
safe-refusal fallback), NOT a quality result - see Items 2-4. Kept for the record; not comparable.

| metric | qwen3:1.7b (baseline @768) | qwen3:4b @768 (truncated) | target | note |
|---|---|---|---|---|
| retrieval_recall | 0.923 | 0.923 | 0.90 | identical (model-independent) - the only valid row |
| citation_recall | 0.875 | 0.000 | - | 0 because nothing was answered |
| citation_grounding_rate | 1.000 | 0.000 | 1.0 | 0 = empty set (no answered questions), not a defect |
| refusal_accuracy | 0.550 | 0.350 | 1.0 | qwen3:4b refused all 20 (truncation), not conservatism |
| faithfulness_rate | 0.000 | 0.000 | 0.95 | no answered questions to judge |
| false answers (of 7 should_refuse) | 0 | 0 | 0 | **safety gate held both runs** |
| in-scope answered (of 13) | 4 | 0 | - | qwen3:4b: 0 (all truncated to empty -> refusal) |

Proof: same prompt -> `max_tokens=768` gives `finish_reason=length`, content_len=0; `max_tokens=4096`
gives `finish_reason=stop`, valid grounded JSON. qwen3:4b needs a larger budget; a fair comparison must
re-run both models at >=2048 (4096 verified).

### Addendum - qwen3:1.7b control at LLM_MAX_TOKENS=4096 (run-label `...-mt4096`)
| metric | qwen3:1.7b @768 | qwen3:1.7b @4096 | delta |
|---|---|---|---|
| retrieval_recall | 0.923 | 0.923 | 0 |
| citation_recall | 0.875 | 0.875 | 0 |
| citation_grounding_rate | 1.000 | 1.000 | 0 |
| refusal_accuracy | 0.550 | 0.550 | 0 |
| in-scope answered (of 13) | 4 | 4 | 0 |

**Identical, per-question (0 differences).** qwen3:1.7b does not truncate at 768 (its reasoning fits,
leaving room for the JSON), so the baseline is a **genuine** result and stands as recorded. The token
budget only confounds qwen3:4b. Net: the qwen3:1.7b baseline is validated; the qwen3:4b quality
comparison remains open pending a 4096 run (heavy).

## Non-goals
- No `app/` code change (run + compare only); no separate/stronger-judge wiring (still a follow-up);
  no corpus/gold/retrieval change; no new dependency.
- **No change to the default model** - qwen3:4b is evaluated as a one-off, not adopted as the default/demo.
- No `retrieval_min_score` tuning (retrieval is not the drag).
- **Never committed:** the generated `report.json` (gitignored), `.env`, `data/*`, `data/eval/gold.jsonl`.

## Caveats
- `qwen3:4b` is heavy (~55-75 s/answer, fan/heat); the run is a deliberate, serial one-off and can be
  aborted if the laptop overheats (re-runnable; deterministic).
- `faithfulness_rate` is still **self-judged** (now by qwen3:4b) - a weak signal; a real judge needs a
  separate slice (small `scripts.evaluate` change + a stronger/keyed judge model).
- `retrieval_recall` is model-independent and only serves as a sanity invariant here.
- N=20 is small; this characterizes the answer-model effect, it does not certify quality.

## Git / workflow (explicit order)
- Start from updated `main` (after the eval-baseline PR merges); branch: **`docs/eval-qwen3-4b-comparison`**.
- Commit order: (1) **this plan file first** (after approval); (2) run the eval and fill the DONE markers +
  comparison table; (3) push + open a PR to `main`. **Never push `main`.**

## Files touched
- `docs/experiments/2026-06-15_eval-stronger-answer-model-comparison-plan.md` (this plan; committed first).
  No `app/` code, no corpus/gold change, no new dependency; `report.json` gitignored (summarized in the marker).
