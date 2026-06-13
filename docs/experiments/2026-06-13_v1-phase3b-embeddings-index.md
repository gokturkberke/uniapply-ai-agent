**Date:** 2026-06-13
**Topic:** V1 Phase 3b - embeddings + Qdrant index (chunks -> searchable vectors)
**Motivation:** Implements note 03 §2/§4 (Qdrant, multilingual embeddings, metadata filtering)
and note 04 §3-4 (semantic vectorization + vector infrastructure with payload filtering).
Completes the ingestion lane by making the Phase 3a chunk artifacts searchable: embed each
chunk and persist vectors + a metadata payload into Qdrant, behind clean Embedder and
VectorStore abstractions. No baseline eval run id exists yet: still pre-retrieval, so there is
nothing to compare against; this phase produces the index that Phase 4 retrieval will query.
**Hypothesis:** Chunks can be embedded and indexed with metadata payloads that enforce
university/programme pre-filtering, verifiable fully offline with a deterministic fake embedder
and an in-memory Qdrant (no model download, no Docker).
**Preconditions:** Phases 1-3a merged to `main`; chunk-artifact contract exists
(`data/chunks/<source_id>.json` = `ChunkingResult`); `.venv` installed; clean working tree on
branch `feat/v1-phase3b-embeddings-index`.

Confirmed: fastembed (ONNX, no torch) real embedder + a deterministic FakeEmbedder for tests;
qdrant-client local mode (on-disk for dev, `:memory:` for tests). Scope guardrails: embeddings +
index build only. NO retrieval policy/ranking/Retrieval Gate/parent-doc fetch, NO `/ask`, NO LLM,
NO API endpoints, NO Docker/Cloud Qdrant (Phase 4+). Reproducibility: pinned model id + deterministic
point ids; embeddings deterministic for a fixed model (no `random_state`).

## 1) Deps, config, .env.example, ignores
- **Goal:** Add the embedding + vector-store deps and config without committing the index.
- **Files:** `requirements.txt`, `app/core/config.py`, `.env.example`, `.gitignore`.
- **Steps:**
  - Add `qdrant-client`, `fastembed` to `requirements.txt` (pin to installed majors; no torch).
  - Add `embedding_provider` (`fastembed`|`fake`), `embedding_model`, `embedding_batch_size`,
    `qdrant_path`, `qdrant_collection` to `Settings`. Verify the fastembed model id against the
    installed version (do not guess).
  - Document ALL new fields in `.env.example` in this same item (repo §3 rule).
  - Gitignore `data/index/`.
- **Test / verification:** `pip install -r requirements.txt`; existing suite green; every Settings
  field has a documented env var.
- **Expected outcome:** Deps + typed config available; index never committed; env docs complete.
- **DONE / DROPPED:**

## 2) Embedder abstraction (app/rag/embeddings.py)
- **Goal:** A model-agnostic embedding interface with an offline-testable fake.
- **Files:** `app/rag/embeddings.py` (new).
- **Steps:**
  - `Embedder` Protocol: `model_id`, `dimension`, `embed_texts`, `embed_query`.
  - `FakeEmbedder(dimension=32)`: deterministic, hash-derived, L2-normalized vectors.
  - `FastEmbedEmbedder(model_id)`: lazy-loaded `fastembed.TextEmbedding` adapter.
  - `get_embedder(settings=None)`: factory by `embedding_provider`.
- **Test / verification:** see item 5.
- **Expected outcome:** Deterministic offline embeddings for tests; real fastembed behind config.
- **DONE / DROPPED:**

## 3) Vector store (app/rag/vector_store.py)
- **Goal:** Wrap qdrant-client local mode with collection + upsert + filtered search.
- **Files:** `app/rag/vector_store.py` (new).
- **Steps:**
  - `from_settings(*, location=None)`: on-disk `qdrant_path` or `:memory:`.
  - `ensure_collection(dimension, *, reset=False)`: Cosine distance.
  - `upsert_chunks(chunks, vectors) -> int`: point id `uuid5(NAMESPACE, chunk_id)`, full payload
    (chunk_id, parent_id, source_id, university_slug, programme_slug, source_authority, lang,
    country_scope, heading_path, text, token_estimate).
  - `search(vector, *, university_slug=None, programme_slug=None, limit=5)`: `models.Filter` pre-filter.
  - `count()`.
- **Test / verification:** see item 5.
- **Expected outcome:** Filterable index; pre-filtering carries the anti-blending guarantee.
- **DONE / DROPPED:**

## 4) Indexing pipeline + CLI (app/rag/indexing.py + scripts/index.py)
- **Goal:** Embed chunk artifacts and populate the collection, offline-testable.
- **Files:** `app/rag/indexing.py` (new), `scripts/index.py` (new).
- **Steps:**
  - `load_chunk_artifacts(chunk_dir)`: yield `(source_id, list[Chunk])` per file (skip `manifest.json`);
    one file at a time (memory-safe).
  - `index_corpus(*, chunk_dir=None, vector_store=None, embedder=None, batch_size=None, reset=True)
    -> IndexResult` (`collection`, `model_id`, `dimension`, `source_count`, `indexed_count`): ensure
    collection (dim from embedder), embed in batches, upsert.
  - `scripts/index.py`: `python -m scripts.index` (real embedder + `VectorStore.from_settings()`);
    "Nothing to index" on empty chunk dir.
- **Test / verification:** see item 5; CLI behavior on an empty chunk dir.
- **Expected outcome:** Deterministic, memory-safe index build with a result summary.
- **DONE / DROPPED:**

## 5) Tests (offline: fake embedder + in-memory Qdrant)
- **Goal:** Prove embeddings, vector store, and indexing offline with zero downloads/Docker.
- **Files:** `tests/test_embeddings.py`, `tests/test_vector_store.py`, `tests/test_indexing.py` (new).
- **Steps:**
  - Embeddings: determinism, dimension, batch length, distinct-text vectors differ.
  - Vector store: `ensure_collection`; `upsert_chunks` -> `count`; filtered `search(university_slug=...)`
    returns only that university (anti-blending); payload round-trips `text`/`source_id`.
  - Indexing: synthetic `ChunkingResult` artifacts for two universities -> `index_corpus` with
    `FakeEmbedder` + in-memory store -> `indexed_count` == chunk count, `count` matches, filtered
    search isolates by university.
- **Test / verification:** `pytest` all green, fully offline, prior tests untouched.
- **Expected outcome:** Green suite; upsert count + metadata isolation covered.
- **DONE / DROPPED:**
