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
- **DONE (commit `e3a4e2c`):** Added pymupdf4llm 1.27 / beautifulsoup4 4.15 / markdownify 1.2
  (pinned to installed majors); gitignored `data/raw/` + `data/normalized/`; added `raw_dir` /
  `normalized_dir` to `Settings`. `pip install -r requirements.txt` resolves; suite stays green.

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
- **DONE (commit `e3a4e2c`):** Added `app/rag/parsers.py` with `parse_pdf`, `parse_html`
  (drops script/style/nav before conversion), and `parse_document` suffix dispatch raising a
  clear `ValueError` on unsupported types.

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
- **DONE (commit `e3a4e2c`):** Added `app/rag/ingestion.py` with `IngestionResult`,
  `normalize_source` (skip on no local_path, `FileNotFoundError` on missing file), and
  `normalize_registry` (reuses `load_registry`, writes a derived `manifest.json`). No fabricated
  `last_updated`.

## 4) Thin CLI entrypoint (scripts/ingest.py)
- **Goal:** A human-triggered offline command to normalize the whole registry.
- **Files:** `scripts/__init__.py` (new), `scripts/ingest.py` (new).
- **Steps:**
  - `python -m scripts.ingest` calls `normalize_registry()` and prints one summary line per
    source (source_id, status, char_count, normalized_path). Logic stays in `app/rag/ingestion.py`.
- **Test / verification:** runs without error against the empty registry (prints nothing to normalize).
- **Expected outcome:** Reproducible offline ingestion entrypoint matching the notes' `scripts/`.
- **DONE (commit `e3a4e2c`):** Added `scripts/__init__.py` + `scripts/ingest.py`; `python -m
  scripts.ingest` prints "Nothing to normalize: registry is empty." against the empty registry.

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
- **DONE (commit `e3a4e2c`):** Added `tests/fixtures/ingestion/sample.html`, `tests/test_parsers.py`,
  and `tests/test_ingestion.py` (PDF generated in `tmp_path`, raw/normalized dirs in `tmp_path`).
  - Metric / result: `pytest` -> 28 passed (20 prior + 8 new). Warnings: pre-existing
    Starlette/httpx + harmless PyMuPDF SWIG-binding deprecations.
  - Decision: Phase 2 complete; normalized Markdown is the input for Phase 3 (chunking + index).

## 6) Document new Settings in .env.example (follow-up)
- **Goal:** Satisfy the repo rule that `.env.example` documents every available variable. The
  `registry_path` (Phase 1) and `raw_dir` / `normalized_dir` (Phase 2, item 1) settings were
  added to `Settings` but not yet documented.
- **Files:** `.env.example`.
- **Steps:**
  - Add `REGISTRY_PATH=data/registry/sources.json`, `RAW_DIR=data/raw`,
    `NORMALIZED_DIR=data/normalized` under a "Registry & ingestion paths" section (active
    settings, not future placeholders).
- **Test / verification:** every `Settings` field has a matching documented variable; `pytest`
  stays green (no behavior change).
- **Expected outcome:** `.env.example` is complete; configuration stays discoverable.
- **DONE (commit `ae05649`):** Added a "Registry & ingestion paths" section to `.env.example`
  documenting `REGISTRY_PATH`, `RAW_DIR`, `NORMALIZED_DIR`. All `Settings` fields now have a
  matching documented variable. `pytest` -> 28 passed (no behavior change).
