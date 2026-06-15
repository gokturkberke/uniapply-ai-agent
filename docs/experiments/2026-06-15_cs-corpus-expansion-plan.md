**Date:** 2026-06-15
**Topic:** CS corpus expansion - add 3 more German CS Master's programmes (5 total), validate scoping at larger N
**Motivation:** The pipeline is validated end to end on the 2-programme CS mini-corpus (Konstanz CIS +
Paderborn CS; registry committed in PR #10) and the local-model work is settled: `qwen3:1.7b` is the
laptop-safe default and a deterministic local smoke (`LOCAL_LLM_TEMPERATURE=0 LOCAL_LLM_SEED=42`) is now
available and reproducible (PR #16). The natural next step before any quality baseline is to **grow the
corpus** so the critical domain rule - never blend facts across institutions - is exercised across more
universities, not just two. This slice adds 3 more CS programmes and validates that retrieval stays
strictly scoped.
**Hypothesis:** The existing pipeline (registry -> ingest -> chunk -> index -> scope-required retrieval ->
grounded-or-refuse) ingests, indexes, and correctly **scopes** a 5-programme CS corpus **with no app code
changes**; each new programme answers an in-scope grounded question with a correct in-scope citation, and
every cross-institution question (a fact specific to programme B asked under programme A's scope) is
**refused** (no blending).
**Preconditions:** V1 + V1.1 + the local-LLM slices merged to `main`; the 2-programme CS registry is
committed; the embedding/index pipeline and the deterministic local smoke both work; Ollama installed with
`qwen3:1.7b`. Inspection (Item 1) confirms no code change is required.

This is a **corpus + docs slice**. It changes the committed registry manifest and the fact-free gold-set
summary, plus the local corpus data (gitignored). It changes **no `app/` code**, no retrieval logic, no
endpoints/schemas/artifacts, and adds no dependency. uni-assist secondary sources keep the existing
**per-scope duplication** (no shared-source mechanism - that remains a separate, future plan).

## Design summary
- **Official page mandatory; uni-assist sources are evidence-gated.** Every programme gets its official
  programme/admissions page (primary). A uni-assist source (VPD and/or processing-time, secondary) is
  added for a programme **only if that programme's official/admissions page confirms uni-assist is part of
  its application route** - concretely, the saved/normalized official page mentions uni-assist, "VPD", or
  "preliminary review documentation (Vorpruefungsdokumentation)". So the per-programme source count is
  **variable (1 to 3)**, not a fixed 3. A programme that applies directly (no uni-assist) carries only its
  official page.
- **Only official pages are new raw files** (one per new programme). The generic uni-assist raw files
  (`uni-assist-vpd.html`, `uni-assist-deadlines-processing-time.html`) already exist and are **reused**
  under per-programme `source_id`s **only where uni-assist is confirmed** (ingestion writes a normalized
  copy per `source_id`).
- **Apply the rule to the existing corpus too.** Re-validate Konstanz CIS + Paderborn CS against the same
  gate and remove any uni-assist source their official page does not support. Per the user, Konstanz CIS
  does **not** require a VPD, so `uni-assist-vpd-konstanz-cis` is a removal candidate (confirm against the
  saved Konstanz page; re-check `uni-assist-processing-time-konstanz-cis` the same way).
- **No fabricated facts:** real official URLs and saved HTML are provided by the user; placeholders are
  valid-but-fake URLs and `last_updated: null` until filled; the gold set asserts no admission facts.
- **`country_scope: ["all"]`** stays (temporary scaffolding, consistent with the current corpus;
  country-aware retrieval is out of scope).

## Suggested programmes (user confirms / swaps at approval)
Three reputable German CS Master's programmes; the user picks the final set, saves each official page, and
fills the real URL + `lang` (`en`, or `de` if the saved page is German). **Each gets its official page;
uni-assist VPD/processing-time is added per programme only if its official page confirms uni-assist
(Item 2's gate) - so a programme may end up with 1, 2, or 3 sources:**

| university_slug (suggested) | programme_slug (suggested) | official-page raw filename | uni-assist? |
|---|---|---|---|
| `technical-university-of-munich` | `msc-informatics` | `tum-msc-informatics.html` | per official page |
| `rwth-aachen-university` | `msc-computer-science` | `rwth-msc-cs.html` | per official page |
| `saarland-university` | `msc-computer-science` | `saarland-msc-cs.html` | per official page |

---

## 1) Inspect (confirm contracts; no change)
- **Goal:** Confirm adding programmes needs only registry + gold + data, no code.
- **Files:** read-only: `app/rag/metadata.py`, `app/rag/registry.py`, `app/rag/evaluation.py`,
  `data/registry/sources.json`, `scripts/ingest.py`/`chunk.py`/`index.py`.
- **Findings:** `RegisteredSource` requires unique kebab-case `source_id`, valid `HttpUrl`, non-empty
  `country_scope`, `source_type` in the existing enum, `primary|secondary` authority; `load_registry`
  rejects duplicate `source_id`s; `filter_sources` isolates by university/programme; `GoldQuestion`
  supports `factual|multi_hop|reformulation|out_of_scope` + `should_refuse`; the current corpus already
  reuses one uni-assist raw file across two scopes -> the same pattern scales with no code change.
- **Test / verification:** findings recorded; no behavior change.
- **DONE (commit `31c1817`):** Confirmed adding programmes needs only registry + gold + data (no code):
  `RegisteredSource` contracts, `load_registry` dedup, `filter_sources` scoping, `GoldQuestion`
  categories, and the existing uni-assist raw-file reuse across scopes all scale unchanged.

## 2) Registry expansion + existing-corpus re-validation (`data/registry/sources.json`)
- **Goal:** Give every programme its official page and attach uni-assist sources **only where confirmed**,
  without fabricating facts - for the 3 new programmes AND the 2 existing ones.
- **Files:** `data/registry/sources.json`.
- **The uni-assist gate (evidence-based, no fabrication):** a programme gets a uni-assist source only if
  its saved/normalized official (or university admissions) page confirms uni-assist is part of the route -
  detected by the page mentioning "uni-assist", "VPD", or "Vorpruefungsdokumentation / preliminary review
  documentation". If the page is silent on uni-assist, **no uni-assist source is added** for that programme.
- **Steps (new programmes):**
  - Always add `<uni>-cs-official-programme-page` (official_page / primary, new raw file).
  - Add `uni-assist-vpd-<uni>-cs` (vpd_info / secondary, reuse `uni-assist-vpd.html`) and/or
    `uni-assist-processing-time-<uni>-cs` (deadline_schedule / secondary, reuse
    `uni-assist-deadlines-processing-time.html`) **only if the gate passes** for that programme.
  - New records: `country_scope: ["all"]`, `lang: "en"` (set `de` if the saved page is German),
    `last_updated: null`, official `url` = `https://example.com/REPLACE_WITH_REAL_URL` until filled
    (uni-assist records reuse the real generic uni-assist URLs already in the registry).
- **Steps (existing programmes - apply the gate retroactively):**
  - Re-check the saved Konstanz CIS and Paderborn CS official pages against the gate. Remove any uni-assist
    source the official page does not support. The user flagged that Konstanz CIS does not require a VPD ->
    remove `uni-assist-vpd-konstanz-cis` unless the saved page actually references uni-assist/VPD; apply the
    same test to `uni-assist-processing-time-konstanz-cis` and to Paderborn's two uni-assist sources.
  - Any removal must also prune/re-scope the gold questions that referenced the removed `source_id`
    (Item 3) and update the summary counts (Item 6).
- **Test / verification:** `load_registry()` loads with no duplicate `source_id`; `filter_sources` isolates
  each programme's scope; each programme's source set matches what its official page supports (>=1 official
  page; uni-assist present only where confirmed). Final record count is **variable** and recorded in the
  DONE marker (not assumed to be 15).
- **Expected outcome:** a manifest where every programme carries exactly the sources its official page
  supports (committed only after URLs are real + the pipeline validates).
- **DONE (recorded):** Final registry = **9 records, 5 programmes**. New: TUM Informatics (+ uni-assist
  VPD/processing, gate passed), Stuttgart CS (official only), Saarland CS (official only); the user swapped
  RWTH -> Stuttgart and filled real URLs. Existing re-validation: **removed both Konstanz uni-assist
  sources** (Konstanz official page has 0 uni-assist/VPD mentions); kept Paderborn's (page routes via
  uni-assist). Gate evidence (normalized official pages): TUM 10 mentions, Paderborn 2 (route only, no
  explicit VPD), Konstanz/Stuttgart/Saarland 0. `load_registry` OK (no duplicate), `filter_sources`
  isolates every scope.

## 3) Gold-set expansion (`data/eval/gold.jsonl`, gitignored; no fabricated facts)
- **Goal:** Exercise the new scopes and, above all, the anti-blending rule.
- **Files:** `data/eval/gold.jsonl` (gitignored); `docs/experiments/eval-goldset-summary.md` (committed
  summary, counts only).
- **Steps (no answers, no admission facts - `expected_source_ids` + `should_refuse` only):**
  - Per new programme: ~3 in-scope questions (factual against the official page; add a multi_hop spanning
    the official page + a uni-assist source **only if that programme actually has a uni-assist source**) ->
    `expected_source_ids` point at that programme's real sources.
  - **Prune/re-scope** any existing gold question whose `expected_source_ids` reference a uni-assist source
    removed in Item 2 (e.g. Konstanz uni-assist questions if those sources are dropped).
  - **Cross-institution refusal questions (the core new value):** ask, under programme A's scope, a fact
    that belongs to a different programme B -> `should_refuse: true`, `expected_source_ids: []`. Add a few
    covering new pairings (e.g. ask a new programme about a Konstanz-specific detail, and vice versa).
  - Keep the existing out-of-scope refusals. Approximate target: ~12 new in-scope + ~3 cross-institution
    refusals (final counts recorded in the DONE marker and the summary file).
  - Eval-set isolation: the gold set stays gitignored and is never used for tuning/few-shot.
- **Test / verification:** `load_gold_set()` parses every question; category counts match the summary.
- **Expected outcome:** a gold set that can both reward correct in-scope grounding and catch blending.
- **DONE (recorded):** Gold set rewritten to **20 questions** (`load_gold_set` parses all; no dangling
  source refs). Category: factual 13, multi_hop 2, reformulation 1, out_of_scope 4; `should_refuse` 7.
  Pruned the 3 Konstanz uni-assist questions; added in-scope questions for TUM/Stuttgart/Saarland and
  single-scope cross-institution VPD traps; converted the Paderborn "VPD docs" question to a
  VPD-explicit **refusal** (official supports the uni-assist route, not VPD) per the source policy.
  `eval-goldset-summary.md` updated (counts/scopes/source_ids/policy, fact-free).

## 4) Manual steps (user) - save raw pages + fill real URLs
- **Goal:** Provide the real corpus inputs without fabricating them.
- **Steps (user):** save the 3 official programme pages under `data/raw/` with the exact filenames from the
  registry (`local_path`); replace each `REPLACE_WITH_REAL_URL` with the real official URL and set `lang`
  to match the saved page; optionally set `last_updated`. The two uni-assist raw files already exist and
  are reused - nothing to re-save for them.
- **Test / verification:** each `local_path` resolves to a saved file under `data/raw/`.
- **DONE (recorded):** User saved the 3 official pages and filled real URLs; swapped Stuttgart to the
  **German** official page (`lang=de`) and Saarland to the **official English** page (`lang=en`) for
  richer/cleaner content (the initial Stuttgart English page was a stub). All `local_path`s resolve under
  `data/raw/` (gitignored).

## 5) Run + validate (pipeline + scoping smoke)
- **Goal:** Prove the expanded corpus ingests/indexes and stays strictly scoped.
- **Steps:**
  - No-network loads: `load_registry` (15) + `filter_sources` per new scope; `load_gold_set` parses all.
  - Rebuild: `python -m scripts.ingest && python -m scripts.chunk && python -m scripts.index`
    (re-indexes all 15 sources; embedding model already cached).
  - Wiring smoke: `LLM_PROVIDER=mock python -m scripts.evaluate --run-label cs-corpus-expansion-mock-smoke`
    (proves end-to-end wiring; the report under `docs/experiments/runs/` is gitignored, not committed).
  - **Scoping smoke (deterministic, the key check):** start the API on a dedicated port with
    `LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 LOCAL_LLM_TEMPERATURE=0
    LOCAL_LLM_SEED=42`, verify the model via `ollama ps`, then **serially**: (a) one in-scope grounded
    `/ask` per new programme (target a fact its actual sources support) -> expect a correct in-scope
    citation; (b) a cross-institution `/ask` (a programme-B fact under programme-A scope) -> expect the
    exact refusal, `citations=[]`. Probes that referenced a removed uni-assist source are re-scoped to a
    source the programme actually has.
- **Test / verification:** loads pass; ingest/chunk/index succeed for all 15; each new programme grounds
  in-scope; every cross-institution probe refuses (no blending). Record outcomes (counts/citation
  `source_id`s/latency; no admission facts, no committed report).
- **Expected outcome:** the pipeline scales to 5 programmes and scoping holds. If a saved page does not
  support an in-scope gold question, the system will (correctly) refuse - prune/adjust that gold question
  rather than asserting a fact not in the corpus.
- **DONE (recorded):** Clean rebuild from raw+registry (after catching and purging stale Konstanz
  uni-assist chunk files that had inflated the index to 11 sources): **144 chunks from 9 sources**.
  `load_registry`(9) + `filter_sources` per scope OK; `load_gold_set`(20) OK. **Retrieval scope checks:
  every scoped query returned only in-scope `source_id`s - zero cross-institution leakage.** Deterministic
  LLM smoke (`qwen3:1.7b`, temp0/seed42, dedicated port, model verified via `ollama ps`) - 6/7 exactly per
  policy: TUM VPD grounded; Paderborn route grounded; Paderborn VPD-explicit / Konstanz VPD / Stuttgart
  VPD-like-TUM / Konstanz cross-trap all refused with no foreign citation; Stuttgart duration grounded.
  One miss: Saarland C1 refused though present (small-model grounding-recall on an "at a glance" table;
  retrieval was sufficient at ~0.49) - a safe failure, not a corpus/scoping defect. (Mock wiring smoke not
  run separately; the deterministic smoke exercised the full `/ask` path across all five scopes.)

## 6) Finalize + record
- **Goal:** Commit the verified corpus + summary + plan markers.
- **Steps:** commit the **verified** `data/registry/sources.json` (real URLs, pipeline validated) + the
  updated `docs/experiments/eval-goldset-summary.md` (new counts/scopes/source_ids, still fact-free) + the
  filled DONE markers; the gold set stays gitignored; push + open a PR to `main`.
- **Decision:** if scoping holds, the expanded corpus is the new baseline corpus and a quantitative eval
  (full `scripts.evaluate` over the expanded gold set) becomes the natural next slice. If a cross-
  institution probe blends, STOP and write a retrieval-scoping fix plan before committing the corpus.
- **DONE (recorded):** Scoping holds (zero blending), so the expanded **5-programme** corpus is the new
  baseline. Committed the verified `data/registry/sources.json` + updated `eval-goldset-summary.md` + this
  plan's markers (gold stays gitignored); the runbook probe-3 re-scope to Paderborn lands as a separate
  commit. Next slice: quantitative eval (`scripts.evaluate`) over the expanded gold set.

## Non-goals
- No `app/` code changes; no retrieval logic change; no endpoints/schemas/artifacts change; no new dependency.
- No shared/global source mechanism (uni-assist stays per-scope duplicated); no country-aware retrieval
  (`country_scope` stays `["all"]`).
- No full quality eval/judge baseline in this slice (the mock smoke proves wiring; the deterministic smoke
  spot-checks scoping). A quantitative eval is the proposed next slice.
- Do NOT fabricate admission facts (URLs/dates are user-provided; the gold set asserts none).
- **Never committed:** `data/raw`, `data/normalized`, `data/chunks`, `data/index`, `data/eval/gold.jsonl`,
  `.env`, Ollama models, and any report under `docs/experiments/runs/`.

## Caveats
- The official pages must actually contain the facts the in-scope gold questions ask; otherwise the gate
  correctly refuses and the question must be pruned/adjusted (not the corpus stretched to assert a fact).
- Adding more institutions raises the blending risk surface; the cross-institution refusal probes are the
  primary guard and must pass.
- The deterministic smoke is a spot-check (small N), not a quantitative baseline.

## Git / workflow (explicit order)
- Start from updated `main`; branch: **`feat/cs-corpus-expansion`**.
- Commit order: (1) **this plan file first** (after approval); (2) registry + gold authored and
  load-validated; (3) user saves raw pages + fills real URLs; (4) run + validate; (5) commit the verified
  `sources.json` + updated summary + DONE markers; (6) push + open a PR to `main`. **Never push `main`.**

## Files touched
- `docs/experiments/2026-06-15_cs-corpus-expansion-plan.md` (this plan; committed first).
- `data/registry/sources.json` (official page per new programme + uni-assist only where the official page
  confirms it; plus removal of any unsupported existing uni-assist sources - variable record count;
  committed only after real URLs + validation).
- `data/eval/gold.jsonl` (expanded; gitignored).
- `docs/experiments/eval-goldset-summary.md` (updated counts; committed). No `app/` code; no new dependency.
