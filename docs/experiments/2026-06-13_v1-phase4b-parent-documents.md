**Date:** 2026-06-13
**Topic:** V1 Phase 4b - parent-document expansion (matched chunks -> parent sections)
**Motivation:** Implements the parent-document pattern from note 03 §4 and note 04 §3 ("Lost in
the Middle"): search on small chunks for precision, but pass the larger surrounding section to the
LLM for synthesis. Phase 4 returns matched child chunks; this slice maps each chunk back to its
`ParentSection` so Phase 5 (`/ask`) can ground generation on full sections. No baseline eval run id
exists yet (still pre-generation); this produces the grounding context the eval harness will judge.
**Hypothesis:** Matched chunks can be mapped to their deduplicated, rank-ordered parent sections,
loaded lazily from the chunk artifacts, verifiable offline with no new dependencies.
**Preconditions:** Phases 1-4 merged to `main`; chunk artifacts carry `parents[]`
(`ChunkingResult`), and `RetrievalResult`/`RetrievedChunk` exist; `.venv` installed; clean working
tree on branch `feat/v1-phase4b-parent-documents`.

Scope guardrails: parent expansion only. NO `/ask`, LLM, or endpoints (Phase 5); NO re-indexing
parents into Qdrant; NO hybrid/rerank (V2). Deterministic; no new `Settings` fields (reuses
`chunk_dir`); no new dependencies.

## 1) Parent store (app/rag/parents.py)
- **Goal:** Lazy, memory-safe lookup of parent sections from chunk artifacts.
- **Files:** `app/rag/parents.py` (new).
- **Steps:**
  - `ParentStore(chunk_dir)`, `from_settings()` (uses `settings.chunk_dir`).
  - `get(source_id, parent_id) -> ParentSection | None`: load `chunk_dir/<source_id>.json` on first
    access for that source (cache `{parent_id: ParentSection}` via `ChunkingResult.model_validate_json`);
    return the parent or `None` (missing file or id). Only referenced sources are read.
- **Test / verification:** see item 4.
- **Expected outcome:** Parent lookups without loading the whole corpus.
- **DONE (commit `c5bd701`):** Added `app/rag/parents.py` with `ParentStore` (lazy per-source load
  + cache, `get`, `from_settings`). Only referenced source files are read.

## 2) Extend retrieval with parent expansion (app/rag/retrieval.py)
- **Goal:** Turn matched chunks into deduplicated parent context.
- **Files:** `app/rag/retrieval.py`.
- **Steps:**
  - Add `parents: list[ParentSection] = Field(default_factory=list)` to `RetrievalResult` (additive;
    `retrieve` keeps returning `parents=[]`).
  - `expand_to_parents(hits, *, parent_store) -> list[ParentSection]`: dedupe by `parent_id` in
    first-appearance order; skip parents not found.
  - `retrieve_with_parents(...)`: `retrieve(...)` then set `result.parents = expand_to_parents(...)`
    (default `ParentStore.from_settings()`); same required `university_slug`.
- **Test / verification:** see item 4.
- **Expected outcome:** Grounding context (parents) available without changing `retrieve`.
- **DONE (commit `c5bd701`):** Added `parents` field to `RetrievalResult` (default empty),
  `expand_to_parents` (dedupe by parent_id in rank order, skip missing), and
  `retrieve_with_parents`. `retrieve` behavior unchanged.

## 3) Surface parents in the search CLI (scripts/search.py)
- **Goal:** Show parent context in the debug entrypoint.
- **Files:** `scripts/search.py`.
- **Steps:**
  - Use `retrieve_with_parents`; print the deduplicated parent sections (source_id, heading_path,
    snippet) alongside hits and the gate decision. Display change only.
- **Test / verification:** argparse wiring intact.
- **Expected outcome:** Manual runs show chunks + parent sections.
- **DONE (commit `c5bd701`):** `scripts/search.py` now uses `retrieve_with_parents` and prints the
  deduplicated parent sections alongside hits + the gate decision. `--help` verified.

## 4) Tests
- **Goal:** Prove parent lookup + expansion offline.
- **Files:** `tests/test_parents.py` (new), `tests/test_retrieval.py` (extend).
- **Steps:**
  - `test_parents.py` (`tmp_path`): write a `ChunkingResult` artifact; `get` returns the parent;
    unknown id -> `None`; missing source file -> `None`.
  - `test_retrieval.py`: `expand_to_parents` dedupes a parent shared by two hits, preserves order,
    and skips an absent parent; `retrieve_with_parents` (in-memory store seeded with chunks + matching
    artifacts in a tmp `chunk_dir`) populates deduped `parents` while `hits` are unchanged.
- **Test / verification:** `pytest` all green, fully offline, prior tests untouched.
- **Expected outcome:** Green suite; dedup/order/skip + end-to-end expansion covered.
- **DONE (commit `c5bd701`):** Added `tests/test_parents.py` (get / unknown id / missing file) and
  extended `tests/test_retrieval.py` (`expand_to_parents` dedupe + skip-missing; `retrieve_with_parents`
  end-to-end populates deduped parents, hits unchanged).
  - Metric / result: `pytest` -> 61 passed (56 prior + 5 new), fully offline.
  - Decision: Phase 4b complete; retrieval is done. Phase 5 (`/ask`) consumes `retrieve_with_parents`.
