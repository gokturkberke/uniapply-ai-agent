**Date:** 2026-06-13
**Topic:** V1 Phase 7 - evaluation harness (RAG-Triad-style metrics over a gold set)
**Motivation:** Implements note 01 (RAG evaluation protocol) and note 03 §6 / note 04 §9 (RAG Triad,
50-question gold set, targets). This is the phase that finally produces a baseline eval run: a custom
in-repo harness replays a gold question set through retrieval + grounded generation and scores
retrieval recall, refusal correctness, citation grounding, and judged faithfulness. The machinery
lands now; real numbers await corpus + gold-set curation (the user's step). Until then there is no
baseline run to compare against - this phase creates the means to generate one.
**Hypothesis:** A custom harness reusing `retrieve_with_parents`, `generate_grounded_answer`,
`format_context`, and the `LLMClient` (as judge) computes retrieval/refusal/grounding/faithfulness
metrics over a gold set, verifiable fully offline with a deterministic MockLLM (answer + judge) and
injected retrieval.
**Preconditions:** Phase 6 merged to `main` (full product surface; `LLMClient`/`MockLLMClient`,
`generate_grounded_answer`, `format_context`, `retrieve_with_parents` all exist); `.venv` installed;
clean working tree on branch `feat/v1-phase7-eval`.

Confirmed: custom harness (no RAGAS/DeepEval); deterministic metrics + LLM-judge faithfulness. Data
hygiene: synthetic gold fixture for tests; real gold set under gitignored `data/eval/`, runs under
gitignored `docs/experiments/runs/` (kept isolated from tuning data, per the no-leakage rule). No new
endpoints, no new deps, no real Anthropic calls in tests. Deterministic (no sampling; pinned models).

## 1) Config + .env.example + gitignore
- **Goal:** Configure the gold-set path and run-output dir; never commit eval data/runs.
- **Files:** `app/core/config.py`, `.env.example`, `.gitignore`.
- **Steps:** add `eval_gold_path: str = "data/eval/gold.jsonl"` and
  `eval_runs_dir: str = "docs/experiments/runs"` to `Settings`; document `EVAL_GOLD_PATH` +
  `EVAL_RUNS_DIR` in `.env.example`; gitignore `data/eval/` and `docs/experiments/runs/`.
- **Test / verification:** settings importable; existing suite green.
- **Expected outcome:** Configurable, isolated eval set + run outputs.
- **DONE (commit `8b89779`):** Added `eval_gold_path` + `eval_runs_dir` to `Settings`; documented
  `EVAL_GOLD_PATH` + `EVAL_RUNS_DIR` in `.env.example`; gitignored `data/eval/` + `docs/experiments/runs/`.

## 2) Eval contracts + harness (app/rag/evaluation.py)
- **Goal:** Gold-set loader, metrics, and an aggregated report, reusing the serving pipeline.
- **Files:** `app/rag/evaluation.py` (new).
- **Steps:**
  - `GoldQuestion(id, question, university_slug, programme_slug=None, category, expected_source_ids=[],
    should_refuse=False)`; `load_gold_set(path) -> list[GoldQuestion]` (JSONL; clear error on bad line).
  - `FaithfulnessVerdict(supported, reasoning)`; `judge_faithfulness(question, answer, retrieval_result,
    *, judge_client)` (strict judge prompt; context via `format_context`).
  - `QuestionResult(id, category, refused, refusal_correct, retrieval_hit: bool|None, faithful: bool|None)`;
    `EvalReport(total, retrieval_recall, refusal_accuracy, faithfulness_rate, by_category, results)`;
    `TARGETS` constant.
  - `evaluate_gold_set(gold, *, answer_client, judge_client, retrieve_fn=retrieve_with_parents)`:
    retrieve -> generate -> `refusal_correct = insufficient_context == should_refuse`; `retrieval_hit` =
    expected ∩ retrieved source_ids (None when no expected ids); `faithful` via judge only when answered;
    aggregate overall + per category.
- **Test / verification:** see item 4.
- **Expected outcome:** Deterministic offline harness producing an `EvalReport`.
- **DONE (commit `8b89779`):** Added `app/rag/evaluation.py` with `GoldQuestion`/`load_gold_set`,
  `FaithfulnessVerdict`/`judge_faithfulness`, `QuestionResult`/`EvalReport`/`TARGETS`, and
  `evaluate_gold_set` (deterministic metrics + judged faithfulness; injectable `retrieve_fn` + clients).

## 3) CLI + synthetic gold fixture
- **Goal:** A runnable evaluation entrypoint + offline test data.
- **Files:** `scripts/evaluate.py`, `tests/fixtures/eval/gold_sample.jsonl` (new).
- **Steps:**
  - `scripts/evaluate.py`: `python -m scripts.evaluate [--run-label LABEL]` -> `load_gold_set`,
    real `get_llm_client` (answer + judge) + settings-backed retrieval, `evaluate_gold_set`, write
    `eval_runs_dir/<label>/report.json`, print summary vs `TARGETS`; "Nothing to evaluate" on empty set.
  - Synthetic fixture: one factual in-scope question (with `expected_source_ids`) + one out-of-scope
    question (`should_refuse=true`).
- **Test / verification:** CLI runs against an empty/absent gold set without error.
- **Expected outcome:** Reproducible eval entrypoint + synthetic gold data.
- **DONE (commit `8b89779`):** Added `scripts/evaluate.py` (`python -m scripts.evaluate --run-label`;
  writes `report.json`, prints metrics vs `TARGETS`; "Nothing to evaluate" on empty/absent gold set,
  verified offline) and `tests/fixtures/eval/gold_sample.jsonl` (a factual + an out-of-scope question).

## 4) Tests (offline; MockLLM)
- **Goal:** Prove loader + judge + aggregation offline.
- **Files:** `tests/test_evaluation.py` (new).
- **Steps:** `load_gold_set` parses the fixture + rejects a malformed line; `judge_faithfulness`
  returns the MockLLM verdict; `evaluate_gold_set` over a synthetic gold set with a stub `retrieve_fn`
  (sufficient + expected source for the factual q; insufficient for out-of-scope) + MockLLM answer
  (cited) + MockLLM judge (supported) -> `EvalReport` with `refusal_accuracy == 1.0`,
  `retrieval_recall == 1.0`, `faithfulness_rate == 1.0`, correct per-category counts; out-of-scope q is
  refused with `retrieval_hit is None` and `faithful is None`.
- **Test / verification:** `pytest` all green, fully offline, prior tests untouched.
- **Expected outcome:** Green suite; metrics/aggregation/refusal-eval covered.
- **DONE (commit `8b89779`):** Added `tests/test_evaluation.py` (loader parse + malformed-line +
  missing-file; judge verdict; `evaluate_gold_set` aggregation -> recall/refusal/faithfulness all 1.0
  on the synthetic gold set; out-of-scope refused with `retrieval_hit`/`faithful` None).
  - Metric / result: `pytest` -> 96 passed (91 prior + 5 new), fully offline.
  - Decision: Phase 7 complete; V1 engineering surface closed. The real baseline run awaits a curated
    corpus + 50-question gold set (user step), then `python -m scripts.evaluate --run-label baseline`.

## 5) Metrics-correctness patch (pre-PR)
- **Goal:** Fix a review finding before opening the PR: `retrieval_recall` was a hit-rate (any expected
  source present), overstating multi-hop baselines; and the plan's "citation grounding" metric was not
  in the report.
- **Files:** `app/rag/evaluation.py`, `scripts/evaluate.py`, `tests/test_evaluation.py`.
- **Steps:**
  - True per-question `retrieval_recall = |expected ∩ retrieved| / |expected|` (mean in the report).
  - Add `citation_recall = |expected ∩ cited| / |expected|` and `citation_grounding = cited ⊆ retrieved`
    (rate in the report); add `citation_grounding_rate` target 1.0.
  - Per-question result now carries `expected_source_ids`, `retrieved_source_ids`, `cited_source_ids`.
  - CLI prints the new metrics; tests: partial recall 0.5 (1 of 2 expected retrieved/cited),
    `_citation_grounding` false for out-of-context, refused questions excluded from citation/faithfulness.
- **Test / verification:** reproduced the inflated recall first; `pytest` green after.
- **Expected outcome:** Metrics reflect true recall and citation grounding; multi-hop no longer overstated.
- **DONE (commit `07bd4db`):** `retrieval_recall` is now true recall (reproduced the inflated 1.0 first;
  now 0.5 for 1-of-2); added `citation_recall` + `citation_grounding_rate` (target 1.0) and the
  per-question source-id lists. `pytest` -> 99 passed.
