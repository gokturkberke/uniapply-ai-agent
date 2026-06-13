**Date:** 2026-06-13
**Topic:** V1 Phase 1 - source registry and metadata contracts
**Motivation:** Implements the first foundational slice of the V1 roadmap: note 04
("Next 5 Tasks" #1, *Registry Setup*) and note 03 (Day 1-2, *Foundation & Registry*).
No baseline eval run id exists yet: the repo is scaffold-only (FastAPI + `/health`), so
there is no prior retrieval/eval run to compare against. This plan establishes the typed
source registry and metadata contracts that every later phase (ingestion, chunking,
retrieval, grounded `/ask`) and the future eval harness (Phase 7) will build on.
**Hypothesis:** A typed, validated source registry with strict university/programme
scoping provides a reusable metadata contract that mechanically prevents cross-institution
blending (the core domain rule), verifiable by focused unit tests, and adds no new runtime
dependencies.
**Preconditions:** Scaffold present (`app/`, `tests/test_api.py` green); `requirements.txt`
installed in `.venv`; clean working tree; docs alignment drift in `AGENTS.md` not yet fixed.

Corresponding research notes: 01 §"Metadata Blueprint" is conceptual; field set is drawn
from note 02 §3, note 03 §3, note 04 §4 (the three converge on university/programme slugs,
source_type, authority, url, last_updated, country_scope, lang).

## 1) Fix docs reference drift in AGENTS.md
- **Goal:** Make the working-loop reference point to the file that actually exists. Root
  `AGENTS.md` line 50 cites `docs/experiments/AGENTS.md` (absent); the real authoritative
  file is `docs/experiments/CLAUDE.md` (which root `CLAUDE.md` already cites correctly).
- **Files:** `AGENTS.md` (line 50 only).
- **Steps:**
  - Replace `docs/experiments/AGENTS.md` with `docs/experiments/CLAUDE.md` on line 50.
  - Do not create a new `docs/experiments/AGENTS.md`; keep a single source of truth.
- **Test / verification:** `grep -rn "docs/experiments/AGENTS.md" .` returns no matches;
  both root agent files now reference `docs/experiments/CLAUDE.md`.
- **Expected outcome:** Documentation is internally consistent; no behavior change.
- **DONE (commit `de372fb`):** Edited `AGENTS.md` line 50 to reference
  `docs/experiments/CLAUDE.md`. Verified `grep` finds no remaining
  `docs/experiments/AGENTS.md` reference outside this plan file; both root agent
  files now agree. No behavior change.

## 2) Add metadata contracts (app/rag/metadata.py)
- **Goal:** Define the canonical, reusable Pydantic v2 metadata contracts for registered
  sources, with validation that mechanically enforces scoping (kebab-case slugs).
- **Files:** `app/rag/__init__.py` (new package marker), `app/rag/metadata.py` (new).
- **Steps:**
  - Enums: `SourceType` (`official_page`, `faq`, `pdf_guide`, `deadline_schedule`,
    `vpd_info`), `SourceAuthority` (`primary`, `secondary`), `Language` (`de`, `en`).
  - `SourceMetadata(BaseModel)`: `university_slug: str`, `programme_slug: str | None`,
    `source_type: SourceType`, `source_authority: SourceAuthority`, `lang: Language`,
    `url: HttpUrl`, `country_scope: list[str]`, `last_updated: date | None = None`.
  - `field_validator`s reject any slug that is not lowercase kebab-case; `country_scope`
    entries normalized/validated to lowercase non-empty tokens.
  - `RegisteredSource(SourceMetadata)`: add `source_id: str` (kebab-case), `title: str`,
    `local_path: str | None = None`. Defer chunk-level fields (`chunk_id`, `page`,
    `parent_id`) to Phase 3.
- **Test / verification:** see item 5 (`tests/test_metadata.py`).
- **Expected outcome:** Importable contracts; invalid slug/url/enum rejected at construction.
- **DONE (commit `96f25d7`):** Added `app/rag/__init__.py` and `app/rag/metadata.py`
  with the three enums and `SourceMetadata` / `RegisteredSource` (kebab-case slug +
  country_scope validators). Chunk-level fields deferred to Phase 3 as planned.

## 3) Add registry loader + empty manifest (app/rag/registry.py, data/registry/sources.json)
- **Goal:** Load and validate a declarative source manifest into typed `RegisteredSource`
  objects and provide a pure, scoped filter (the anti-blending query path).
- **Files:** `app/rag/registry.py` (new), `data/registry/sources.json` (new, `[]`).
- **Steps:**
  - `load_registry(path: Path | None = None) -> list[RegisteredSource]`: resolve `path`
    from `get_settings().registry_path` when None; read JSON; validate each entry; raise
    `ValueError` with a clear message on malformed JSON or duplicate `source_id`. Empty
    array is valid and returns `[]`.
  - `filter_sources(sources, *, university_slug=None, programme_slug=None,
    source_authority=None) -> list[RegisteredSource]`: pure in-memory filter.
  - Create `data/registry/sources.json` as `[]`. No invented/guessed URLs; real entries
    are added in Phase 2 only after manual verification.
- **Test / verification:** see item 5 (`tests/test_registry.py`).
- **Expected outcome:** Default-path load returns `[]`; scoped filters isolate by slug.
- **DONE (commit `96f25d7`):** Added `app/rag/registry.py` (`load_registry` with clear
  errors on malformed JSON, non-list payload, and duplicate `source_id`; pure
  `filter_sources`) and `data/registry/sources.json` as `[]`. No guessed URLs committed.

## 4) Wire registry_path into Settings (app/core/config.py)
- **Goal:** Keep all configuration typed and centralized; no `os.environ` reads in domain code.
- **Files:** `app/core/config.py`.
- **Steps:**
  - Add `registry_path: str = "data/registry/sources.json"` to `Settings`.
  - `load_registry` consumes it via the existing `get_settings()` singleton.
- **Test / verification:** covered indirectly by the default-path test in item 5.
- **Expected outcome:** Registry location is configurable via env without code changes.
- **DONE (commit `96f25d7`):** Added `registry_path: str = "data/registry/sources.json"`
  to `Settings`; `load_registry` resolves it via the existing `get_settings()` singleton.

## 5) Tests + fixtures (tests/test_metadata.py, tests/test_registry.py, tests/fixtures/)
- **Goal:** Prove validation, uniqueness, scoped filtering, and cross-institution isolation
  with focused, fixture-driven tests that do not depend on the production manifest's contents.
- **Files:** `tests/fixtures/registry_sample.json` (synthetic), `tests/test_metadata.py`,
  `tests/test_registry.py`.
- **Steps:**
  - Synthetic fixture: universities `uni-alpha` / `uni-beta`, `https://example.org/...`
    URLs, mixed authorities/langs. Synthetic on purpose - asserts nothing about real schools.
  - `test_metadata.py`: valid models construct; uppercase/space slug rejected; bad `url`
    rejected; bad enum rejected; `last_updated` defaults to `None`.
  - `test_registry.py`: fixture loads to expected count; duplicate `source_id` raises;
    `filter_sources(university_slug="uni-alpha")` returns only `uni-alpha` (assert zero
    `uni-beta` leakage); unknown slug -> `[]`; malformed manifest written to `tmp_path`
    raises a clear error; committed empty `data/registry/sources.json` loads to `[]`.
- **Test / verification:** `pytest` all green, including untouched `tests/test_api.py`.
- **Expected outcome:** Green suite; anti-blending guarantee covered by an explicit test.
- **DONE (commit `96f25d7`):** Added `tests/fixtures/registry_sample.json` (synthetic),
  `tests/test_metadata.py`, and `tests/test_registry.py` including the cross-institution
  isolation test and the empty committed-manifest load.
  - Metric / result: `pytest` -> 20 passed, 1 pre-existing Starlette/httpx warning.
  - Decision: Phase 1 complete; foundation ready for Phase 2 (ingestion).
