**Date:** 2026-06-13
**Topic:** V1 Phase 3a - structure-aware chunking (normalized Markdown -> chunks)
**Motivation:** Implements note 02 §5 (structure-aware chunking) and note 04 §3 (structural
chunking + the parent-document pattern). Turns the normalized Markdown produced in Phase 2
into the searchable chunk units a vector index will later hold, while validating chunk quality
before any embeddings/indexing exist. No baseline eval run id exists yet: the repo is still
pre-retrieval, so there is nothing to compare against; this phase produces the chunk corpus
that Phase 3b will embed and index.
**Hypothesis:** Header-bounded chunking with parent/source linkage produces deterministic,
size-bounded chunks that preserve section structure and carry the source's scoping metadata,
verifiable on synthetic fixtures with no new dependencies.
**Preconditions:** Phases 1-2 merged to `main` (registry + metadata contracts + normalized
Markdown contract present); `.venv` installed; clean working tree on branch
`feat/v1-phase3a-chunking`.

Scope guardrails (explicitly confirmed): chunking + chunk metadata + parent/source linkage +
deterministic artifacts + offline tests only. NO embeddings, sentence-transformers, torch,
model downloads, Qdrant, Docker, vector store interfaces, retrieval, LLM calls, or API
endpoints (those are Phase 3b+). Chunking is deterministic, so no `random_state` applies.

## 1) Config + ignores
- **Goal:** Add chunk sizing + output-dir config without committing derived corpora.
- **Files:** `app/core/config.py`, `.gitignore`.
- **Steps:**
  - Add `chunk_dir: str = "data/chunks"`, `chunk_max_tokens: int = 600`,
    `chunk_overlap_tokens: int = 80` to `Settings`.
  - Gitignore `data/chunks/`.
- **Test / verification:** existing suite still green; settings importable.
- **Expected outcome:** Configurable chunk sizing/output; derived chunks never committed.
- **DONE / DROPPED:**

## 2) Chunk-level metadata contracts (app/rag/metadata.py)
- **Goal:** Define the chunk/parent contracts deferred from Phase 1.
- **Files:** `app/rag/metadata.py` (extend).
- **Steps:**
  - `ParentSection`: `parent_id`, `source_id`, `heading_path: list[str]`, `text`.
  - `Chunk`: `chunk_id`, `parent_id`, `source_id`, `heading_path`, `text`, `token_estimate`,
    plus denormalized scoping fields copied from the source (`university_slug`,
    `programme_slug`, `source_authority`, `lang`, `country_scope`) for later payload filtering.
  - `ChunkingResult`: `source_id`, `parents: list[ParentSection]`, `chunks: list[Chunk]`.
- **Test / verification:** see item 5.
- **Expected outcome:** Importable chunk contracts carrying the anti-blending scope fields.
- **DONE / DROPPED:**

## 3) Chunker logic (app/rag/chunking.py)
- **Goal:** Pure, deterministic, header-aware chunking with overlap and a size bound.
- **Files:** `app/rag/chunking.py` (new).
- **Steps:**
  - `estimate_tokens(text) -> int`: whitespace word-count proxy (documented approximation; pluggable).
  - `split_into_sections(markdown) -> list[Section]`: header-bounded sections with `heading_path`
    breadcrumbs; pre-header content -> `heading_path=[]`.
  - `chunk_markdown(markdown, source, *, max_tokens=None, overlap_tokens=None,
    token_estimator=estimate_tokens) -> ChunkingResult`: each section is a parent; fits -> one
    verbatim chunk; oversized -> greedy paragraph packing with `overlap_tokens` overlap, word-window
    fallback for an over-budget paragraph. Stable ids `parent_id`/`chunk_id`. Defaults from settings.
- **Test / verification:** see item 5.
- **Expected outcome:** Deterministic chunks within the token budget, structure preserved.
- **DONE / DROPPED:**

## 4) Chunking pipeline + artifacts (app/rag/chunking.py + scripts/chunk.py)
- **Goal:** Run chunking over the registry and persist artifacts; offer an offline entrypoint.
- **Files:** `app/rag/chunking.py`, `scripts/chunk.py` (new).
- **Steps:**
  - `chunk_source(source, *, normalized_dir, chunk_dir, ...)`: read `normalized_dir/<source_id>.md`
    (`FileNotFoundError` if absent), `chunk_markdown`, write `chunk_dir/<source_id>.json`.
  - `chunk_corpus(sources=None, *, normalized_dir=None, chunk_dir=None, ...)`: reuse `load_registry`;
    chunk sources with a normalized file, record others `skipped_not_normalized`; write
    `chunk_dir/manifest.json` summary.
  - `scripts/chunk.py`: `python -m scripts.chunk` prints a per-source summary.
- **Test / verification:** see item 5; CLI runs cleanly against the empty registry.
- **Expected outcome:** Per-source chunk artifacts + manifest; memory-safe (one source at a time).
- **DONE / DROPPED:**

## 5) Tests + synthetic fixture
- **Goal:** Prove the chunker and pipeline offline with zero real content.
- **Files:** `tests/fixtures/chunking/sample_normalized.md` (new), `tests/test_chunking.py` (new).
- **Steps:**
  - Fixture: synthetic normalized Markdown with multiple `##`/`###` headers, a short section, and
    a deliberately long section that forces splitting.
  - Tests (offline, `tmp_path`): section parsing + heading_path; small->one verbatim chunk;
    oversized->multiple chunks each within `chunk_max_tokens`, overlapping, unique/ordered ids,
    parent links valid, scoping fields equal the source's, determinism (twice -> identical);
    `chunk_source` writes JSON + missing-file `FileNotFoundError`; `chunk_corpus` statuses + manifest.
- **Test / verification:** `pytest` all green, fully offline, including untouched prior tests.
- **Expected outcome:** Green suite; structure/size/overlap/linkage/determinism covered.
- **DONE / DROPPED:**
