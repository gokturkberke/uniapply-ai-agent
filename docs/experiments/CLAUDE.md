# Plan & experiment file format (docs/experiments/)

This directory is the project's memory. Every plan and its execution outcome lives here, commit-traceable and grep-able. The rules below define exactly how plan files are named, structured, and marked. This file is loaded automatically whenever you create or edit anything under `docs/experiments/`.

## Where the plan file goes, and what it is named
- All new plans are saved under `docs/experiments/`.
- Filename format: `{YYYY-MM-DD}_{plan-name}.md` (kebab-case plan name).
  Example: `2026-06-13_chunk-size-sweep.md`, `2026-06-20_citation-prompt-revisit.md`.
- The date is the day the plan was **authored**, not the day it was executed. The filename stays fixed even if the plan spans multiple experiments over several days.
- Do not touch code before the plan file exists. In the `Inspect -> Plan -> Code -> Test -> Fix` loop, the plan file is the artifact produced by the `Plan` step.

## Required structure of the plan file
- A plan file is written **item by item**, **in logical order**, as a **narrative**:
  motivation -> hypothesis -> preconditions -> items -> expected outputs -> decision criteria.
- Header block at the top of every plan file:
  - **Date:** {YYYY-MM-DD}
  - **Topic:** short title
  - **Motivation:** which report section (`§X`) or which eval-metric anomaly triggered this plan; link the baseline eval run id(s) so comparisons stay reproducible.
  - **Hypothesis:** the proposition under test, expressed as a measurable claim (e.g. "reducing chunk size from 1000 to 500 tokens improves retrieval recall@5 by at least 3pp").
  - **Preconditions:** code / config / index state that must already be in place before the plan starts.
- Then a numbered list of items (`## 1) ...`, `## 2) ...`). Template for each item:
  - **Goal:** what will change (code / config / sweep parameter).
  - **Files:** paths to touch (with line numbers or function names). Use glob patterns when applicable (e.g. `config/rag/*.yaml`).
  - **Steps:** sub-bullets, one logical operation per bullet (e.g. "set `retrieval.chunk_size: 500` in config", "run the eval harness on the dev question set and capture the log").
  - **Test / verification:** which unit test gets added or updated; which eval-run output is compared against which metric table (e.g. recall@k, answer faithfulness, citation accuracy).
  - **Expected outcome:** decision criterion (e.g. how big a recall@5 delta counts as meaningful, where faithfulness should land relative to the target band).
  - **DONE / DROPPED:** empty at authoring time; filled in during execution (see below).
- Items are ordered by the **narrative**: dependencies before dependents, independents in parallel. The flow "test the hypothesis with a single config -> if positive, expand to a sweep -> production decision" must always be visible. Random ordering is not acceptable.

## Execution / marking contract
- Each time an item is executed, write the outcome **into the same file**, **immediately under that item**. Template:
  ```
  **DONE (commit `<hash>`):** {one or two sentences: what changed, which behavior was gained, any remaining side-effect.}
  - Metric / result: {small baseline-vs-experiment table if relevant}
  - Run id: {always include, found under `docs/experiments/runs/{run_id}/`}
  - Sweep JSON: {if applicable, path under `docs/experiments/...sweep_...json`}
  - Decision: {shipped to production, shelved, or fed into another experiment}
  ```
- The `<hash>` placeholder must never be left in place; do not write DONE before the commit lands. If the execution required multiple commits, list all of them in order, comma-separated.
- For abandonment, the marker becomes `DROPPED ({date}):` followed by a one-paragraph reason. No item is left open; every item is closed as either DONE or DROPPED.
- Outside the plan file, the audit report (`docs/experiments/2026-06-13_full_report.md`) keeps cross-references across multiple plans. If a new plan resolves a specific audit item (e.g. §3.5 chunk overlap), the plan file carries a `Corresponding audit item: §3.5` line, and the audit item is annotated with `see: docs/experiments/2026-06-20_citation-prompt-revisit.md`.
- Any change landing in production config (`config/rag.yaml`) as the outcome of a plan / experiment must carry an inline comment that points back to the plan file or report `§` (e.g. `# experiment 4 (report §14): chunk_size=500`). This is how a config reader finds the rationale behind a value.

## A plan file does NOT contain
- Speculative "might also try" lists beyond the concrete intent. A plan is the contract for **work happening now**, not a wishlist.
- Re-summaries of already-closed plans. A cross-reference link is enough.
- Pasted code blocks. A plan file is prose + bullets; code changes live in the commit.

## Pre-flight (before creating a new plan file)
- `grep` under `docs/experiments/` for a half-open plan on the same topic. If one exists, append a new item to that plan file. Do not create a new one.
- Record the current benchmark / baseline eval run id before the plan starts (write it in the **Motivation** section). This is what later makes statements like "experiment X is +3pp recall@5 vs baseline" reproducible.

## Commit and push contract (CRITICAL)
- Every experiment item that lands a DONE or DROPPED marker MUST be committed in the same change set as the plan-file update. No experiment outcome is allowed to sit in the working tree uncommitted.
- Every plan-file edit (new plan, new item, marker fill, framing revision) MUST be committed as soon as the edit stabilizes. A plan file is not a scratchpad; every revision must be commit-traceable.
- After the commit lands, push to remote in the same step. The working tree must return to a clean state (`git status` empty) before moving to the next item.
- The `<hash>` placeholder in DONE markers is filled with the actual commit hash post-push; never leave the literal `<hash>` text in committed plan files.
- If multiple items finish in parallel, batch them into one commit but keep the per-item DONE/DROPPED markers explicit. Do not combine unrelated experiments into a single commit.
- Scratch/exploratory artifacts (`scratch/`, `notebooks/_*.json`, ad-hoc runners) are gitignored by convention; only the plan file + reproducible runner scripts + final config patches get committed.
