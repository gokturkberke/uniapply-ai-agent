**Date:** 2026-06-18
**Topic:** Artifact over-refusal + quality fix (Checklist / Detect-missing) (roadmap PR 2)
**Motivation:** With the local model (qwen3:1.7b), the Checklist tool refused on every programme tested and
Detect-missing returned page labels instead of documents. Proven root cause (reproduced, not guessed): the
checklist's structured JSON is **truncated** at low token budgets - a diagnostic on TUM Informatics raised
`LLMOutputError: Invalid JSON: EOF while parsing a list` (output cut off mid `items` list); `safe_generate`
(`app/rag/generation.py:191-194`) catches it and silently returns `_checklist_refusal()`. The same input at
`LLM_MAX_TOKENS=2048` parsed cleanly (4 grounded items). The app default budget is 4096 (works); the `768`
"laptop-safe" value introduced in PR 1 (`make run-local` + README) is what truncates. Checklist overflows
first because its JSON is the longest artifact output. Detect-missing's "Start of study / ECTS Credits" output
is a separate prompt-specificity issue, not truncation. This is a delivery/prompt-tuning slice, so the header
carries a measurable **Goal** instead of a Hypothesis.
**Goal:** The artifact tools stop over-refusing and produce sensible output with the laptop-safe local model,
by bounding artifact output (so the JSON stays small + higher quality), right-sizing the demo budget for
headroom, and sharpening the Detect-missing prompt. No retrieval, contract, or grounding/citation change.
**Preconditions:** PR 1 (provider visibility) merged to `main`; branch `feat/artifact-quality` off `main`;
working tree clean; Ollama on the host with `qwen3:1.7b` for the local-model smoke.

Out of scope: retrieval/index changes, response-contract changes, a retry/JSON-repair mechanism (only added
if verification shows bounded prompts + budget are insufficient), draft-email (benefits incidentally from the
budget headroom), and switching the default demo model.

---

## 1) Right-size the artifact generation budget
- **Goal:** Give structured artifact JSON enough budget to complete (the proven truncation cause).
- **Files:** `Makefile` (`run-local`), `README.md`, `.env.example` (comment only).
- **Steps:** raise the demo budget `LLM_MAX_TOKENS` from `768` to `1536` in `run-local` and the README local
  runbook; fix the `.env.example` comment that recommends 768 (it truncates structured artifacts; recommend
  >=1536 for the artifact tools). No new Settings field (`llm_max_tokens` exists; default 4096).
- **Test / verification:** checklist completes (no `LLMOutputError`) at 1536 across the 5 programmes; raise to
  2048 only if a programme still truncates.
- **Expected outcome:** Checklist no longer truncated at the demo budget.
- **DONE / DROPPED:**

## 2) Bound + sharpen the Checklist prompt
- **Goal:** Compact, higher-quality checklist that fits a modest budget.
- **Files:** `app/rag/artifacts.py` (`generate_checklist` system prompt).
- **Steps:** instruct at most ~8 of the most important items, each `detail` one concise sentence. Leave the
  refusal/grounding logic (lines 96-99) unchanged.
- **Test / verification:** offline artifact tests stay green; local-model smoke shows grounded items.
- **Expected outcome:** concise grounded checklists, no truncation.
- **DONE / DROPPED:**

## 3) Sharpen the Detect-missing prompt
- **Goal:** Extract real required documents/credentials, not page section labels.
- **Files:** `app/rag/artifacts.py` (`detect_missing_documents` system prompt).
- **Steps:** explicitly define "required documents/credentials an applicant must submit or hold" (e.g. degree
  certificate, transcript, language certificate, CV, statement of purpose, VPD) and instruct it NOT to list
  page sections, field labels, or procedural steps; keep items short.
- **Test / verification:** local-model smoke on a programme shows document-like items, not labels.
- **Expected outcome:** missing/satisfied lists read as real documents.
- **DONE / DROPPED:**

## 4) Verification + regression test
- **Goal:** Prove the fix and lock the truncation behavior offline.
- **Files:** `tests/test_artifacts.py`.
- **Steps:** add a regression test - a fake `LLMClient` raising `LLMOutputError` makes `generate_checklist`
  and `detect_missing_documents` return the canonical refusal (locks "truncation degrades to a clean refusal,
  never a 500"); run the local-model smoke (`make run-local`, Ollama up) across the 5 programmes recording
  refusal + item counts before vs after.
- **Test / verification:** `pytest` green; frontend `npm test`/`build` green (untouched); smoke recorded.
- **Expected outcome:** measurable drop in artifact refusals; offline suite green.
- **DONE / DROPPED:**

---

## Non-goals
- No retrieval/embedding/index change; no response-contract change (`insufficient_context` semantics intact).
- No retry/JSON-repair unless verification shows bounded prompts + budget insufficient (then a one-shot retry
  at a higher budget, per the repo's no-over-defensive rule).
- Draft-email not targeted (benefits incidentally); default demo model unchanged (qwen3:1.7b).

## Git / workflow
- Branch `feat/artifact-quality` off `main`. Commit order: this plan -> budget (item 1) -> checklist prompt
  (item 2) -> detect-missing prompt (item 3) -> regression test (item 4) -> docs + DONE markers (with
  before/after smoke). `pytest` green; push + PR. Tree clean between items.

## Files touched
- `app/rag/artifacts.py`; `Makefile`; `README.md`; `.env.example` (comment); `tests/test_artifacts.py`.
- New plan: `docs/experiments/2026-06-18_artifact-over-refusal-plan.md`. No new dependency.
