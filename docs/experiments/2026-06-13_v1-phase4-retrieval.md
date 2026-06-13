**Date:** 2026-06-13
**Topic:** V1 Phase 4 - retrieval (metadata pre-filter + dense search + Retrieval Gate)
**Motivation:** Implements note 03 §4 (Retrieval-First) and note 04 §5 (the retrieval loop:
query embed -> metadata pre-filter -> dense search -> Retrieval Gate; hybrid/RRF/rerank are
explicitly V2). First serving-lane slice: turn the indexed chunks into a scope-required dense
retriever with a deterministic refusal signal that Phase 5 (`/ask`) will key off. No baseline eval
run id exists yet: still pre-generation, so nothing to compare against; this phase produces the
retrieval contract the eval harness (Phase 7) will measure.
**Hypothesis:** A scope-required dense retriever with a score gate returns only the target
university/programme's chunks and flags insufficient context deterministically, verifiable offline
with a fake embedder + in-memory Qdrant.
**Preconditions:** Phases 1-3b merged to `main`; `VectorStore.search` (university/programme filter)
and `Embedder`/`get_embedder` exist; `.venv` installed; clean working tree on branch
`feat/v1-phase4-retrieval`.

Scope guardrails: retrieval logic only. NO `/ask`, LLM, or API endpoints (Phase 5); NO
parent-document expansion (Phase 4b - parents live in chunk artifacts, not the index); NO
hybrid/BM25/RRF/cross-encoder rerank (V2). `retrieve()` requires `university_slug` (anti-blending
enforced at the boundary). Deterministic; no `random_state`.

## 1) Config + .env.example
- **Goal:** Make top-K and the gate threshold configurable and documented.
- **Files:** `app/core/config.py`, `.env.example`.
- **Steps:**
  - Add `retrieval_top_k: int = 5`, `retrieval_min_score: float = 0.3` to `Settings`.
  - Document `RETRIEVAL_TOP_K`, `RETRIEVAL_MIN_SCORE` in `.env.example` (note: min_score is a
    cosine-similarity placeholder to calibrate against the Phase 7 eval set).
- **Test / verification:** settings importable; existing suite green.
- **Expected outcome:** Tunable retrieval; env docs complete.
- **DONE (commit `c0e9d5b`):** Added `retrieval_top_k` (5) + `retrieval_min_score` (0.3) to
  `Settings`; documented `RETRIEVAL_TOP_K` + `RETRIEVAL_MIN_SCORE` in `.env.example` (min_score
  noted as a placeholder to calibrate in Phase 7).

## 2) Retrieval contracts + logic (app/rag/retrieval.py)
- **Goal:** Embed -> metadata pre-filter -> dense top-K -> Retrieval Gate, returning scored chunks.
- **Files:** `app/rag/retrieval.py` (new).
- **Steps:**
  - `RetrievedChunk`: `chunk: Chunk` + `score: float`.
  - `RetrievalResult`: `query`, `university_slug`, `programme_slug`, `hits`, `sufficient_context`,
    `top_score`.
  - `retrieve(query, *, university_slug, programme_slug=None, top_k=None, min_score=None,
    embedder=None, vector_store=None)`: defaults from settings; `embed_query` ->
    `VectorStore.search(filter, limit=top_k)`; rebuild hits via `Chunk.model_validate(payload)`;
    gate `sufficient_context = bool(hits) and hits[0].score >= min_score`. `university_slug`
    keyword-only + required.
- **Test / verification:** see item 4.
- **Expected outcome:** Scope-required retriever with a deterministic gate.
- **DONE (commit `c0e9d5b`):** Added `app/rag/retrieval.py` with `RetrievedChunk`, `RetrievalResult`,
  and `retrieve()` (keyword-only required `university_slug`; reuses `VectorStore.search` filtering
  and `get_embedder`; gate `sufficient_context = top hit score >= min_score`). Hits rebuilt via
  `Chunk.model_validate(point.payload)`.

## 3) Search CLI (scripts/search.py)
- **Goal:** Manual retrieval/debug entrypoint.
- **Files:** `scripts/search.py` (new).
- **Steps:**
  - `python -m scripts.search "<query>" --university <slug> [--programme <slug>]`: real embedder +
    `VectorStore.from_settings()`; print hits (score, source_id, heading_path, snippet) +
    `sufficient_context`.
- **Test / verification:** argparse wiring; logic stays in `retrieval.py`.
- **Expected outcome:** Reproducible manual query path.
- **DONE (commit `c0e9d5b`):** Added `scripts/search.py` (`python -m scripts.search "<q>"
  --university <slug> [--programme <slug>]`) printing hits + the gate decision; argparse `--help`
  verified (no embedder/index touched).

## 4) Tests (tests/test_retrieval.py) - offline
- **Goal:** Prove scope isolation, top-K, and the gate offline.
- **Files:** `tests/test_retrieval.py` (new).
- **Steps:**
  - Seed in-memory `VectorStore` (FakeEmbedder) with two universities + two programmes in one.
  - Institution isolation; university+programme isolation; `top_k` honored; gate True at
    `min_score=-1.0` and False at `min_score=1.01`; unknown scope -> empty + insufficient;
    `university_slug` required (`TypeError`).
- **Test / verification:** `pytest` all green, fully offline, prior tests untouched.
- **Expected outcome:** Green suite; scope + gate behavior covered.
- **DONE (commit `c0e9d5b`):** Added `tests/test_retrieval.py` (7 tests: institution isolation,
  university+programme isolation, top_k, gate pass at min_score=-1.0, gate refuse at min_score=1.01,
  unknown-scope empty+insufficient, required `university_slug`).
  - Metric / result: `pytest` -> 56 passed (49 prior + 7 new), fully offline.
  - Decision: Phase 4 complete. Phase 4b adds parent-document expansion; Phase 5 builds `/ask` on
    top of `sufficient_context`.
