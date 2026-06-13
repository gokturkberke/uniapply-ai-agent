**Date:** 2026-06-13
**Topic:** V1 Phase 2 - ingestion normalization (raw PDF/HTML -> Markdown)
**Motivation:** Implements note 03 Day 3-4 (Ingestion Pipeline) and note 04 §2 (Ingestion
Pipeline and Document Normalization). Builds the offline ingestion-lane step that every
later phase depends on: turning manually-downloaded raw documents into structured Markdown
that preserves headers and tables (so Phase 3 chunking keeps requirements intact). No
baseline eval run id exists yet: the repo is still pre-retrieval (registry + contracts only),
so there is nothing to compare against; this phase produces the normalized corpus that the
Phase 7 eval harness will eventually measure.
**Hypothesis:** Layout-aware normalization to Markdown preserves heading/table/list structure
verifiably on synthetic fixtures, using a lightweight, swappable parser backend
(pymupdf4llm for PDF, beautifulsoup4 + markdownify for HTML) with no network access and no
new endpoints.
**Preconditions:** Phase 1 merged to `main` (registry + metadata contracts present, including
`RegisteredSource.local_path`); `.venv` installed; clean working tree on branch
`feat/v1-phase2-ingestion`.

Scope guardrails: offline only (no fetching/crawling, per the §44b manual-download posture and
the V1 "no live web crawling" non-goal); synthetic fixtures only (no real/guessed sources
committed); no chunking, embeddings, vector DB, or LLM (Phase 3+).

## 1) Dependencies, ignores, and config
- **Goal:** Add the lightweight parsing stack and the storage-dir config without committing corpora.
- **Files:** `requirements.txt`, `.gitignore`, `app/core/config.py`.
- **Steps:**
  - Add `pymupdf4llm`, `beautifulsoup4`, `markdownify` to `requirements.txt` (pinned to current
    stable majors).
  - Gitignore `data/raw/` and `data/normalized/`; leave `data/registry/sources.json` tracked.
  - Add `raw_dir: str = "data/raw"` and `normalized_dir: str = "data/normalized"` to `Settings`.
- **Test / verification:** `pip install -r requirements.txt` succeeds; existing suite still green.
- **Expected outcome:** Parsing deps available; derived corpora never committed; dirs configurable.
- **DONE / DROPPED:**

## 2) Parser backends + dispatch (app/rag/parsers.py)
- **Goal:** Convert a single PDF/HTML file to Markdown behind a swappable suffix dispatch.
- **Files:** `app/rag/parsers.py` (new).
- **Steps:**
  - `parse_pdf(path: Path) -> str` via `pymupdf4llm.to_markdown`.
  - `parse_html(path: Path) -> str` via `BeautifulSoup` (drop `script`/`style`/`nav`) + `markdownify`.
  - `_PARSERS_BY_SUFFIX` mapping + `parse_document(path) -> str`; raise a clear `ValueError`
    on unsupported suffixes. Small explicit functions; no ABC hierarchy.
- **Test / verification:** see item 5 (`tests/test_parsers.py`).
- **Expected outcome:** Both formats normalize to non-empty Markdown; unknown types rejected.
- **DONE / DROPPED:**

## 3) Normalization pipeline (app/rag/ingestion.py)
- **Goal:** Normalize registered sources from the raw archive into the normalized layer.
- **Files:** `app/rag/ingestion.py` (new).
- **Steps:**
  - `IngestionResult(BaseModel)`: `source_id`, `raw_path`, `normalized_path`, `parser`,
    `char_count`, `status`.
  - `normalize_source(source, *, raw_dir, normalized_dir)`: resolve `raw_dir/local_path`;
    `None` local_path -> `skipped_no_local_path`; missing file -> `FileNotFoundError`; else
    parse and write `<normalized_dir>/<source_id>.md`. No intermediate temp files.
  - `normalize_registry(sources=None, *, raw_dir=None, normalized_dir=None)`: default from
    `load_registry()` + settings; normalize each; write derived `<normalized_dir>/manifest.json`.
  - Do NOT fabricate `last_updated`; it is user-curated manifest metadata, read-only here.
- **Test / verification:** see item 5 (`tests/test_ingestion.py`).
- **Expected outcome:** Deterministic, offline normalization with a derived output manifest.
- **DONE / DROPPED:**

## 4) Thin CLI entrypoint (scripts/ingest.py)
- **Goal:** A human-triggered offline command to normalize the whole registry.
- **Files:** `scripts/__init__.py` (new), `scripts/ingest.py` (new).
- **Steps:**
  - `python -m scripts.ingest` calls `normalize_registry()` and prints one summary line per
    source (source_id, status, char_count, normalized_path). Logic stays in `app/rag/ingestion.py`.
- **Test / verification:** runs without error against the empty registry (prints nothing to normalize).
- **Expected outcome:** Reproducible offline ingestion entrypoint matching the notes' `scripts/`.
- **DONE / DROPPED:**

## 5) Tests + synthetic fixtures
- **Goal:** Prove parsing and the pipeline offline, with zero real/copyrighted content.
- **Files:** `tests/fixtures/ingestion/sample.html` (new), `tests/test_parsers.py` (new),
  `tests/test_ingestion.py` (new).
- **Steps:**
  - Synthetic HTML fixture with an `<h2>`, a `<table>`, and a `<ul>`.
  - `test_parsers.py`: HTML -> Markdown preserves heading/table/list text; PDF -> Markdown
    (build a tiny PDF in `tmp_path` via PyMuPDF, then parse); `parse_document` routes by
    suffix and raises `ValueError` on an unsupported type.
  - `test_ingestion.py` (use `tmp_path` for raw/normalized dirs): `normalize_source` writes
    `<source_id>.md` with `char_count > 0`; missing raw file -> `FileNotFoundError`;
    `local_path=None` -> `skipped_no_local_path`; `normalize_registry` returns results and
    writes `manifest.json`.
- **Test / verification:** `pytest` all green, fully offline, including untouched Phase 1 tests.
- **Expected outcome:** Green suite; structure-preservation and error paths covered.
- **DONE / DROPPED:**
