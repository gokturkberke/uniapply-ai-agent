# Computer Science mini-corpus baseline

- **Date:** 2026-06-14
- **Topic:** First real ingested corpus: a 4-document, 2-programme Computer Science mini-corpus, replacing the never-downloadable TUM/Data-Science placeholder registry, to establish the first reproducible end-to-end baseline.
- **Motivation:** There is **no prior committed eval run** and **no real baseline**. The evaluation harness landed in commits `8b89779` and `07bd4db`, but the registry it runs against has only placeholder entries (`url: https://example.com/REPLACE_WITH_REAL_URL`, `.pdf` files that were never downloaded) sitting uncommitted in the working tree (`git HEAD` has `data/registry/sources.json` as `[]`). Nothing has ever been ingested, so every metric to date is vacuous. This plan creates the first genuinely ingestible corpus so the harness has real documents to retrieve over.
- **Hypothesis:** A 4-HTML-file corpus mapped to 6 programme-scoped registry entries across two CS programmes (University of Konstanz, Paderborn University) parses cleanly through the existing `.html` ingestion lane and produces a usable index. Concretely, measurable as: `python -m scripts.ingest` normalizes 6/6 sources with non-zero `char_count`; `python -m scripts.chunk` yields >0 chunks for all 6; `python -m scripts.index` indexes >0 chunks from 6 sources; and the mock-provider eval replays end-to-end without error. A *meaningful* real baseline (non-zero `retrieval_recall`, `refusal_accuracy = 1.0` on the out-of-scope questions) additionally requires the gold set to be re-scoped to these two programmes first (Item 7).
- **Preconditions:**
  - `.venv` active with `requirements.txt` installed (`pymupdf4llm`, `beautifulsoup4`, `markdownify`, `fastembed`, `qdrant-client`, `pydantic-settings`, `anthropic`).
  - HTML ingestion already supported: `app/rag/parsers.py` dispatches `.html`/`.htm` to `parse_html`. No code change needed for parsing.
  - `data/registry/sources.json` currently holds **uncommitted** TUM placeholders; `HEAD` is `[]`. Tests do not read this file (they use `tests/fixtures/registry_sample.json`), so replacing it does not affect `pytest`. **Correction (execution):** this was inaccurate - `tests/test_registry.py::test_committed_empty_manifest_loads_to_empty_list` *does* read the committed manifest and asserted it empty; landing the verified corpus turned it red, and it was updated (and renamed to `test_committed_manifest_holds_verified_cs_corpus`) to assert the six-source manifest. See Item 4.
  - `fastembed` downloads `paraphrase-multilingual-MiniLM-L12-v2` on first real index run (network needed once).
  - Real baseline (Item 6, phase B) additionally needs `ANTHROPIC_API_KEY`; the mock smoke (phase A) needs no key and no network beyond the one-time embedding-model download.

---

## 1) Why switch from the TUM/Data-Science idea to a CS mini-corpus

- **Goal:** Record the rationale so the corpus choice is commit-traceable; make no code change in this item.
- **Steps / reasoning:**
  - The TUM/Data-Science entries were never real: `url` is the literal `REPLACE_WITH_REAL_URL` placeholder and the referenced `.pdf` files do not exist in `data/raw/`. Running `scripts.ingest` against them raises `FileNotFoundError`. They are scratch placeholders, not a baseline.
  - The four chosen pages are official, stable, English-language HTML, and freely fetchable without login: two university programme pages plus two uni-assist procedural pages (VPD guidance, deadlines/processing time). They exercise the `.html` lane and the primary-vs-secondary `source_authority` distinction the generator already relies on.
  - Two programmes (Konstanz CIS, Paderborn CS) let us prove the **anti-blending guarantee** end-to-end: programme-scoped retrieval must never return Paderborn chunks for a Konstanz query and vice versa.
- **Test / verification:** N/A (framing item).
- **Expected outcome:** The decision and its constraints are written down before any file changes.
- **DONE (commit `0bb62c0`):** Rationale recorded. The TUM/Data-Science entries were confirmed never-real (placeholder `example.com` URLs, absent `.pdf` files) and replaced by the real CS corpus. Decision: the two-programme CS mini-corpus is the first real baseline.

## 2) Official sources used

- **Goal:** Pin the exact upstream URLs the corpus is built from.
- **Sources:**
  - University of Konstanz - M.Sc. Computer and Information Science (programme page): `https://www.uni-konstanz.de/en/study/before-you-study/study-programmes/detail/computer-and-information-science/`
  - Paderborn University - M.Sc. Computer Science (programme page): `https://www.uni-paderborn.de/en/studyoffer/course_of_study/computer-science-master`
  - uni-assist - Plan your application (VPD guidance): `https://www.uni-assist.de/en/how-to-apply/plan-your-application/`
  - uni-assist - Deadlines and processing time: `https://www.uni-assist.de/en/how-to-apply/plan-your-application/deadlines-processing-time/`
- **Test / verification:** Download gate in Item 3 (each file must contain its expected marker text).
- **Expected outcome:** Four reachable official pages identified; the two uni-assist pages are shared procedural sources reused under both programme scopes (Item 4).
- **DONE (commit `0bb62c0`):** All four official English pages fetched over plain `curl` (no bot-block); the two uni-assist pages are reused under both programme scopes.

## 3) Local filenames created (download into `data/raw/`)

- **Goal:** Manually download the four pages into the gitignored raw archive and prove each download is real content, not a bot-block/consent interstitial.
- **Files (created, gitignored):**
  - `data/raw/konstanz-msc-cis.html`
  - `data/raw/paderborn-msc-cs.html`
  - `data/raw/uni-assist-vpd.html`
  - `data/raw/uni-assist-deadlines-processing-time.html`
- **Steps:**
  ```bash
  mkdir -p data/raw
  curl -L "https://www.uni-konstanz.de/en/study/before-you-study/study-programmes/detail/computer-and-information-science/" -o data/raw/konstanz-msc-cis.html
  curl -L "https://www.uni-paderborn.de/en/studyoffer/course_of_study/computer-science-master" -o data/raw/paderborn-msc-cs.html
  curl -L "https://www.uni-assist.de/en/how-to-apply/plan-your-application/" -o data/raw/uni-assist-vpd.html
  curl -L "https://www.uni-assist.de/en/how-to-apply/plan-your-application/deadlines-processing-time/" -o data/raw/uni-assist-deadlines-processing-time.html
  ```
- **Test / verification (this is the download gate):**
  ```bash
  ls -lh data/raw
  grep -i "Computer and Information Science" data/raw/konstanz-msc-cis.html
  grep -i "Computer Science"                  data/raw/paderborn-msc-cs.html
  grep -i "VPD"                               data/raw/uni-assist-vpd.html
  grep -i "processing"                        data/raw/uni-assist-deadlines-processing-time.html
  ```
- **Risk / fallback:** German university and uni-assist sites may return a `403`, a cookie-consent interstitial, or JS-rendered shells to a bare `curl`. If any `grep` finds nothing or a file is implausibly small, the download is bad. Retry with a browser User-Agent (`curl -L -A "Mozilla/5.0 ..."`); if still blocked, save the page from a browser ("Save As -> Web Page, HTML only") into the same path. Do not proceed to Item 4 until all four greps pass.
- **Expected outcome:** Four non-empty HTML files whose marker text confirms real content.
- **DONE (commit `0bb62c0`):** Downloaded into `data/raw/` (gitignored), sizes 40K-152K. Grep gate passed: Konstanz "Computer and Information Science" x13, Paderborn "Computer Science" x29, uni-assist "VPD" x4, deadlines "processing" x13. No User-Agent / browser-save fallback was needed.

## 4) How `data/registry/sources.json` is updated

- **Goal:** Replace the uncommitted TUM placeholders with six programme-scoped CS entries. Four HTML files, six entries: the two uni-assist files are duplicated under each programme scope (no shared/global-source mechanism is introduced here; that stays a separate, separately-approved plan).
- **Files:** `data/registry/sources.json` (full replacement of the array).
- **Schema note:** Beyond the fields named in the task (`source_id`, `source_type`, `source_authority`, `university_slug`, `programme_slug`, `url`, `local_path`, `last_updated`), the Pydantic `RegisteredSource` model **also requires** `title`, `lang`, and a non-empty `country_scope`. All entries below set `lang: en`, `country_scope: ["all"]` (matching existing convention; uni-assist VPD requirements are in reality country-specific, but we will not fabricate country scoping in this slice), and `last_updated: null` (we do not fabricate a source's last-updated date; ingestion treats it as read-only/user-curated).
- **Proposed entries (one row per `source_id`):**

  | source_id | local_path (in data/raw/) | university_slug | programme_slug | source_type | source_authority |
  |---|---|---|---|---|---|
  | `konstanz-cis-official-programme-page` | `konstanz-msc-cis.html` | `university-of-konstanz` | `msc-computer-and-information-science` | `official_page` | `primary` |
  | `uni-assist-vpd-konstanz-cis` | `uni-assist-vpd.html` | `university-of-konstanz` | `msc-computer-and-information-science` | `vpd_info` | `secondary` |
  | `uni-assist-processing-time-konstanz-cis` | `uni-assist-deadlines-processing-time.html` | `university-of-konstanz` | `msc-computer-and-information-science` | `deadline_schedule` | `secondary` |
  | `paderborn-cs-official-programme-page` | `paderborn-msc-cs.html` | `paderborn-university` | `msc-computer-science` | `official_page` | `primary` |
  | `uni-assist-vpd-paderborn-cs` | `uni-assist-vpd.html` | `paderborn-university` | `msc-computer-science` | `vpd_info` | `secondary` |
  | `uni-assist-processing-time-paderborn-cs` | `uni-assist-deadlines-processing-time.html` | `paderborn-university` | `msc-computer-science` | `deadline_schedule` | `secondary` |

  - `url` per entry: the official-page rows use their programme URL from Item 2; the four uni-assist rows use the two uni-assist URLs (VPD rows -> `.../plan-your-application/`, processing-time rows -> `.../deadlines-processing-time/`). The two uni-assist URLs repeat across programme scopes; that is allowed (uniqueness is enforced only on `source_id`, not `url`).
  - `title` per entry: a short human label, e.g. "University of Konstanz - M.Sc. Computer and Information Science (programme page)", "uni-assist - Plan your application (VPD guidance)", "uni-assist - Deadlines and processing time".
- **Consequence to note (intentional):** ingestion writes one normalized `{source_id}.md` per entry, so each shared uni-assist HTML is normalized into two scoped Markdown files (four total from the two uni-assist files). This is the cost of duplicating procedural sources per scope until a shared-source mechanism exists.
- **Test / verification:** `python -c "from app.rag.registry import load_registry; print(len(load_registry()))"` returns `6` with no `ValidationError` (proves slugs, `HttpUrl`, enums, and `source_id` uniqueness all pass).
- **Expected outcome:** A valid 6-entry registry; no placeholder/`example.com` URLs remain.
- **DONE (commit `0bb62c0`):** `data/registry/sources.json` replaced with the six programme-scoped entries; `load_registry()` returns 6 with no `ValidationError` and no `example.com`/placeholder URLs. `last_updated` left `null` and `country_scope` `["all"]` (no fabrication). Same commit updated the registry guard test (the precondition-correction above): `test_committed_empty_manifest_loads_to_empty_list` was renamed to `test_committed_manifest_holds_verified_cs_corpus` and now asserts the six expected `source_id`s.

## 5) Commands: ingest -> chunk -> index -> evaluate

- **Goal:** Run the offline pipeline end-to-end over the new corpus.
- **Steps:**
  ```bash
  source .venv/bin/activate
  python -m scripts.ingest      # normalize 6 sources -> data/normalized/*.md + manifest.json
  python -m scripts.chunk       # parents + child chunks -> data/chunks/
  python -m scripts.index       # embed + upsert into local Qdrant (data/index/qdrant)
  LLM_PROVIDER=mock python -m scripts.evaluate --run-label cs-mini-corpus-mock-smoke
  ```
- **Test / verification:**
  - `ingest`: 6 lines, each `status=normalized` with non-zero `char_count`. A `FileNotFoundError` means a registered `local_path` has no file in `data/raw/` (re-check Item 3).
  - `chunk`: 6 lines, each with `chunk_count > 0`.
  - `index`: prints `Indexed N chunks from 6 sources` with `N > 0` and the pinned `model=...MiniLM-L12-v2`.
  - mock smoke: writes `docs/experiments/runs/cs-mini-corpus-mock-smoke/report.json` and exits 0. Metric values are expected to be poor here (see Item 7); the smoke gate is "runs clean over the new index", not a metric bar.
- **Expected outcome:** Pipeline integrity proven on real CS documents.
- **DONE (commit `0bb62c0`):** Pipeline ran end-to-end over the new corpus. ingest 6/6 `normalized` (26190/6888/8271/31597/6888/8271 chars); chunk 23/4/10/24/4/10 chunks; index 75 chunks from 6 sources (`model=paraphrase-multilingual-MiniLM-L12-v2`, dim 384); mock smoke ran clean.
  - Run id: `cs-mini-corpus-mock-smoke`
  - Note: fastembed warns this model now uses mean pooling instead of CLS (a fastembed-version behavior, pre-existing, not introduced here); pin fastembed 0.5.1 if byte-identical vectors are required for a future comparison.

## 6) Success criteria

- **Goal:** Define exactly what counts as a passing baseline, split into the two phases.
- **Phase A - mock smoke (no key, this plan):** all four pipeline stages succeed; 6/6 sources normalized with content; >0 chunks each; >0 chunks indexed from 6 sources; `cs-mini-corpus-mock-smoke/report.json` written; `pytest` still green (it does not touch the production registry, so it should be unaffected).
- **Phase B - real baseline (needs `ANTHROPIC_API_KEY`, gated on Item 7):**
  ```bash
  # set in the local .env (never committed):
  #   LLM_PROVIDER=anthropic
  #   ANTHROPIC_API_KEY=<real key>
  python -m scripts.evaluate --run-label cs-mini-corpus-baseline
  ```
  produces `docs/experiments/runs/cs-mini-corpus-baseline/report.json`. A *meaningful* baseline requires the gold set to be re-scoped first (Item 7). Target reference bands (from `app/rag/evaluation.py::TARGETS`): `retrieval_recall >= 0.90`, `refusal_accuracy = 1.0`, `citation_grounding_rate = 1.0`, `faithfulness_rate >= 0.95`. For a first baseline these are aspirational, not pass/fail gates; the deliverable is a real, reproducible measurement plus the recorded metrics, not hitting every band on the first try.
- **Reproducibility:** embedding model and `claude-opus-4-8` are pinned; the eval harness is deterministic given a fixed gold set and pinned models. Record the run id and metric table in this plan's DONE markers (the raw `report.json` stays gitignored under `runs/`).
- **Test / verification:** as above per phase.
- **Expected outcome:** Phase A passes within this plan; Phase B is recorded once Item 7 is resolved and a key is available.
- **DONE (commit `0bb62c0`) - Phase A only:** Phase A smoke gate met (4 stages clean, 6/6 normalized with content, >0 chunks each, 75 indexed, report written, `pytest` 99 passed). **Phase B (real Anthropic baseline) NOT run** - deferred pending an `ANTHROPIC_API_KEY` per the operator's instruction; it stays open until that run lands.
  - Metric / result (mock smoke - only `retrieval_recall` is LLM-independent and meaningful here):

    | metric | value | note |
    |---|---|---|
    | retrieval_recall | 0.750 | real signal; 10 in-scope questions |
    | citation_recall | 0.000 | MockLLM artifact (empty citations) |
    | citation_grounding_rate | 0.000 | MockLLM artifact |
    | refusal_accuracy | 0.167 | MockLLM artifact (empty citations force refusal) |
    | faithfulness_rate | 0.000 | MockLLM artifact |

  - Run id: `cs-mini-corpus-mock-smoke`
  - Anti-blending verified: every Konstanz query retrieved only `*-konstanz-cis` sources and every Paderborn query only `*-paderborn-cs` sources (zero cross-institution leakage).
  - Decision: corpus + pipeline shipped. Real baseline (`run-label cs-mini-corpus-baseline`) pending the key. Two recall misses flagged for a future tuning experiment: `konstanz-factual-deadline` retrieved the processing-time page instead of the labeled official page, and three multi_hop questions retrieved only 1 of 2 expected sources within `top_k=5`.

## 7) Eval gold-set coupling (DRIFT - decision required before Phase B)

- **Goal:** Surface and resolve a contradiction the corpus switch creates, rather than masking it.
- **Drift:** `data/eval/gold.jsonl` is hard-bound to the old corpus - every question carries `university_slug: tum-munich`, `programme_slug: msc-data-science`, and `expected_source_ids` of `tum-msc-ds-admission` / `uni-assist-vpd`. After the CS switch none of those slugs or ids exist in the index, so programme-scoped retrieval returns nothing: `retrieval_recall` -> 0 on factual/multi-hop, and the mock/real generator refuses (empty context fails the Retrieval Gate), so `refusal_accuracy` collapses (only the 2 out-of-scope questions stay correct). `data/eval/` is gitignored, so `gold.jsonl` is a local artifact and any change to it is not committed.
- **Options:**
  - **Option A (recommended):** After downloads (Item 3) and before Phase B, re-scope `data/eval/gold.jsonl` to the two CS programmes - swap `university_slug`/`programme_slug`, repoint `expected_source_ids` to the new CS `source_id`s, rewrite the Munich-specific reformulation question, and keep the two out-of-scope refusal questions. Gold questions contain only question text + `expected_source_ids` + `should_refuse` (no admission answers), so authoring them from the page/registry structure neither fabricates admission facts nor tunes on model output. This yields a meaningful Phase B baseline.
  - **Option B:** Keep this plan corpus-only. Run Phase A mock smoke to prove pipeline integrity, and defer Phase B (real baseline) + the gold-set migration to a separate, separately-approved plan.
- **Test / verification:** under Option A, `python -c "from app.rag.evaluation import load_gold_set; print({q.university_slug for q in load_gold_set()})"` returns only the two CS universities; the eval replay then shows non-zero `retrieval_recall` and `refusal_accuracy = 1.0` on the out-of-scope questions.
- **Expected outcome:** A conscious choice is recorded; Phase B does not run against a mismatched gold set by accident.
- **DONE (commit `0bb62c0`) - Option A:** Re-scoped `data/eval/gold.jsonl` (gitignored) from TUM/Data-Science to the two CS programmes: 12 questions across only the two CS universities, all six `source_id`s referenced, categories factual 6 / multi_hop 3 / reformulation 1 / out_of_scope 2. Authored from slugs, source-ids, refusal flags, and question text only - no admission facts fabricated. Decision: Option A executed so Phase B will run against a matched gold set.

## 8) What must NOT be committed

- **Goal:** Keep derived/copyrighted material and secrets out of git.
- **Steps / verification:** confirm via `git status` that the working tree, after the corpus run, stages **only** this plan file and `data/registry/sources.json`.
  - Gitignored, never committed (verified in `.gitignore`): `data/raw/`, `data/normalized/`, `data/chunks/`, `data/index/`, `data/eval/` (so `gold.jsonl` too), and `docs/experiments/runs/` (so both `report.json` files).
  - Never commit a real `.env` or any real `ANTHROPIC_API_KEY`; the key lives only in the local `.env`.
  - Do not commit placeholder or unverified registry entries: `data/registry/sources.json` is committed **only after** Item 5 Phase A passes over the real downloads.
  - Do not fabricate admission facts anywhere (registry `last_updated`, titles, country scope, or gold answers).
- **Expected outcome:** The only committed artifacts are this plan (with filled DONE markers + metric tables) and the verified 6-entry registry.
- **DONE (commit `0bb62c0`):** Across the two commits only `data/registry/sources.json`, `tests/test_registry.py`, and this plan file are staged/committed. `git check-ignore` confirms `data/raw/`, `data/normalized/`, `data/chunks/`, `data/index/`, `data/eval/gold.jsonl`, and `docs/experiments/runs/.../report.json` are ignored and uncommitted. No real `ANTHROPIC_API_KEY` committed.

---

### Execution order (once approved)
1. Item 3 - download the four HTML files; pass the grep gate.
2. Item 7 - confirm Option A vs B (this is the one decision that changes what runs).
3. Item 4 - rewrite `data/registry/sources.json` to the six CS entries; validate via `load_registry`.
4. (Option A only) re-scope `data/eval/gold.jsonl` to the CS programmes.
5. Item 5 - ingest -> chunk -> index -> mock smoke.
6. Item 6 Phase B - real baseline (if a key is available and Item 7 resolved).
7. Item 8 - commit this plan (with DONE markers + metrics) and `data/registry/sources.json`; push; confirm `git status` clean.
