**Date:** 2026-06-15
**Topic:** Quantitative eval baseline of the 5-programme CS corpus (deterministic local generation)
**Motivation:** The CS corpus was expanded to 5 programmes / 9 evidence-gated sources
(`2026-06-15_cs-corpus-expansion-plan.md`, PR `feat/cs-corpus-expansion`). Scoping was spot-checked with a
deterministic local smoke (retrieval scope checks + 6/7 policy-correct probes), but we have **no
quantitative numbers** over the full gold set. This slice runs the in-repo eval harness
(`scripts.evaluate`) over the 20-question gold set and records the metric table against the harness'
reference `TARGETS` (faithfulness 0.95, retrieval_recall 0.90, refusal_accuracy 1.0,
citation_grounding_rate 1.0).
**Hypothesis (measurable):** With deterministic local generation (`qwen3:1.7b`, `LLM_MAX_TOKENS=768`,
`LOCAL_LLM_TEMPERATURE=0`, `LOCAL_LLM_SEED=42`), over the 20-question gold set: `retrieval_recall >= 0.90`
(retrieval is scope-correct and model-independent) and `citation_grounding_rate == 1.0` (citations are
filtered to retrieved context by construction). `refusal_accuracy` is dragged below 1.0 mainly by
small-model false refusals on well-supported in-scope facts (the recorded Saarland C1 case), and
`faithfulness_rate` is reported but treated as a **weak** signal because the same small local model judges
its own answers.
**Preconditions:** corpus expansion merged to `main`; the local index + 20-question gold set are built
(`data/index/qdrant`, `data/eval/gold.jsonl`, both gitignored); Ollama running with `qwen3:1.7b`. The eval
runs in-process (no uvicorn) and **serially** (one answer + at most one judge call per question), so no
parallel Ollama requests.

This is a **docs-only run-and-record slice**: no `app/` code, no retrieval/corpus/gold/endpoint/schema
changes. The generated `report.json` is gitignored; the metric numbers are summarized in the DONE marker.

## Design summary
- One command: `scripts.evaluate --run-label <label>` with the deterministic local env. It replays the
  gold set through `retrieve_with_parents` + `generate_grounded_answer`, scores the five metrics, writes
  `docs/experiments/runs/<label>/report.json` (gitignored), and prints the summary vs `TARGETS`.
- **What each metric reflects** (so interpretation is grounded, not guessed):
  - `retrieval_recall` - expected ∩ retrieved / expected; **model-independent** (pure retrieval).
  - `refusal_accuracy` - `refused == should_refuse`; driven by the **answer** model (deterministic here).
  - `citation_recall` / `citation_grounding_rate` - from the answer's citations; grounding should be 1.0
    because `generate_grounded_answer` drops out-of-context citations.
  - `faithfulness_rate` - LLM-as-judge; here the judge is the **same** `qwen3:1.7b` (self-judging) -> weak.
- The harness function `evaluate_gold_set` accepts separate `answer_client` / `judge_client`, but
  `scripts.evaluate` currently passes one client to both. A separate (stronger) judge would need a small
  CLI/env addition **and** a stronger model (an API key or a heavier local model) - both out of scope here.

---

## 1) Inspect (confirm harness contracts; no change)
- **Goal:** Confirm exactly how the eval scores and where its output lands, so the run is reproducible.
- **Files:** read-only: `app/rag/evaluation.py`, `scripts/evaluate.py`, `app/core/config.py`.
- **Findings:** `scripts.evaluate --run-label L` -> `evaluate_gold_set(gold, answer_client=c, judge_client=c)`
  -> `docs/experiments/runs/L/report.json` (gitignored) + printed summary. Metrics as above; `retrieval_recall`
  is model-independent; faithfulness uses the (here self-) LLM judge; the loop is serial.
- **Test / verification:** findings recorded; no behavior change.
- **DONE / DROPPED:**

## 2) Run the deterministic local eval
- **Goal:** Produce the quantitative metric table over the 20-question gold set, reproducibly.
- **Files:** none (run-only); the report is gitignored, numbers go in the DONE marker.
- **Steps:**
  - Confirm `ollama` is up with `qwen3:1.7b` and the local index exists.
  - Run (serial, in-process):
    `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 LOCAL_LLM_TEMPERATURE=0
    LOCAL_LLM_SEED=42 python -m scripts.evaluate --run-label cs-corpus-expansion-local-qwen3-1.7b`
  - Capture the printed metric table + `by_category`, and (from `report.json`) the per-question breakdown.
- **Test / verification:** the run completes for all 20 questions; `report.json` written under the
  gitignored runs dir.
- **Expected outcome:** `retrieval_recall >= 0.90`, `citation_grounding_rate == 1.0`; `refusal_accuracy`
  high but possibly < 1.0; `faithfulness_rate` reported (weak signal).
- **DONE / DROPPED:**

## 3) Interpret (per-metric, per-question; no fabrication)
- **Goal:** Turn the numbers into specific, grounded findings - which questions drag which metric.
- **Steps:** for each metric below target, list the offending question ids from `report.json` and classify
  the fault layer:
  - low `retrieval_recall` -> expected source not in top-k: chunking / source-text / `retrieval_min_score`
    (a separate tuning slice, not fixed here).
  - `refusal_accuracy` < 1.0 -> **false refusal** (in-scope, well-supported question refused: small-model
    grounding-recall, e.g. Saarland C1) vs **false answer** (a `should_refuse` question answered: a
    blending / gate concern - higher severity). Separate the two.
  - low `citation_recall` -> answered + grounded but cited a different in-scope source than expected
    (adjust gold expectation, not the corpus).
  - `citation_grounding_rate` < 1.0 -> would indicate a real defect (cited a non-retrieved source); expect 1.0.
  - `faithfulness_rate` -> reported only; do not treat the self-judged number as a quality verdict.
- **Test / verification:** every below-target metric has a named cause and a fault-layer label.
- **Expected outcome:** a short, concrete findings list (especially the false-refusal set).
- **DONE / DROPPED:**

## 4) Decision + record
- **Goal:** Record the baseline and the next lever without changing code/corpus in this slice.
- **Decision rule:**
  - If **any `should_refuse` question was answered** (a false answer / possible blend), that is the
    highest-priority finding -> STOP and open a retrieval/grounding fix plan before anything else.
  - Else record the baseline. False refusals on well-supported facts -> candidate next slices: a heavier
    answer model run (e.g. `qwen3:4b`, accepting the latency/heat) for an answer-quality comparison, and/or
    `retrieval_min_score` calibration if `retrieval_recall` is the drag.
  - The model default is unchanged; the corpus and gold are unchanged in this slice.
- **Files:** this plan (DONE markers + metric table). Report stays gitignored.
- **Test / verification:** metric table + decision captured in the marker.
- **DONE / DROPPED:**

## Metric table (filled at execution; numbers only, no admission facts)
| metric | value | target | notes |
|---|---|---|---|
| total | | 20 | |
| retrieval_recall | | 0.90 | model-independent |
| citation_recall | | - | expectation-sensitive |
| citation_grounding_rate | | 1.0 | expect 1.0 by construction |
| refusal_accuracy | | 1.0 | false-refusal drag expected |
| faithfulness_rate | | 0.95 | weak: self-judged by qwen3:1.7b |
| by_category | | - | |

## Non-goals
- No `app/` code change (run + interpret only); no separate/stronger judge wiring (needs a key or a
  heavier judge + a small CLI change - a future slice).
- No `retrieval_min_score` tuning, no chunking changes, no corpus or gold edits in this slice (findings may
  propose them as follow-ups).
- No change to the default model; no new dependency.
- **Never committed:** the generated `report.json` under `docs/experiments/runs/` (gitignored), `.env`,
  `data/*`, or `data/eval/gold.jsonl`.

## Caveats
- `faithfulness_rate` is **self-judged** by the same small local model -> a weak signal, reported not relied on.
- `refusal_accuracy` / `citation_*` reflect the deterministic `qwen3:1.7b` answer model; a stronger answer
  model would likely raise them (especially the Saarland in-scope facts) - quantifying that is a follow-up.
- N=20 is a small gold set; the baseline characterizes, it does not certify.

## Git / workflow (explicit order)
- Start from updated `main` (after the corpus-expansion PR merges); branch: **`docs/cs-corpus-eval-baseline`**.
- Commit order: (1) **this plan file first** (after approval); (2) run the eval and fill the DONE markers +
  metric table with the recorded numbers; (3) push + open a PR to `main`. **Never push `main`.**

## Files touched
- `docs/experiments/2026-06-15_cs-corpus-eval-baseline-plan.md` (this plan; committed first). No `app/`
  code, no corpus/gold change, no new dependency; `report.json` gitignored (summarized in the marker).
