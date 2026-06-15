# Evaluation Gold Set — Summary (structure only)

This is a **fact-free** structural summary of the evaluation gold set. The gold set itself
(`data/eval/gold.jsonl`) is **gitignored** and kept isolated from any tuning/few-shot data. This
document deliberately contains **no question answers and no admission facts** (deadlines, fees,
language requirements, required documents, eligibility) — only counts, categories, scopes, and the
`source_id`s the questions are expected to retrieve from.

## Totals
- Questions: **20**
- `should_refuse: true`: **7**

## By category
| category | count |
|---|---|
| factual | 13 |
| multi_hop | 2 |
| reformulation | 1 |
| out_of_scope | 4 |

## By scope (university_slug / programme_slug)
| scope | count |
|---|---|
| university-of-konstanz / msc-computer-and-information-science | 6 |
| paderborn-university / msc-computer-science | 7 |
| technical-university-of-munich / msc-informatics | 2 |
| university-of-stuttgart / msc-computer-science | 2 |
| saarland-university / msc-computer-science | 3 |

## Referenced source_ids (expected retrieval targets for non-refusal questions)
- `konstanz-cis-official-programme-page`
- `paderborn-cs-official-programme-page`
- `uni-assist-processing-time-paderborn-cs`
- `tum-informatics-official-programme-page`
- `uni-assist-vpd-tum-informatics`
- `stuttgart-cs-official-programme-page`
- `saarland-cs-official-programme-page`

(Two registered sources — `uni-assist-vpd-paderborn-cs`, `uni-assist-processing-time-tum-informatics` —
are intentionally not the expected target of any non-refusal question; they are procedural sources, and
VPD-required questions are refusal questions per the source policy below.)

## Source policy encoded by the gold set
- Programme-specific admission facts must be supported by the **official** university/programme page.
- Generic uni-assist pages are **procedural only** and cannot establish whether a specific programme
  requires a VPD; they are cited only after the official page establishes that the programme uses
  uni-assist/VPD.
- **Silence is unsupported, not a negative fact.** If an official page does not mention VPD, a
  "does this programme require a VPD?" question is a **refusal** (exact refusal string), not an answer
  of "no". Only TUM's official page establishes VPD explicitly; Konstanz/Paderborn/Stuttgart/Saarland
  VPD-required questions therefore refuse (Paderborn's page supports the uni-assist application *route*
  but does not state VPD explicitly).
- Anti-blending is tested with **single-scope cross-institution traps** (e.g. under one programme's
  scope, ask about another programme's VPD requirement) — expected: exact refusal, no foreign citation.
  No multi-programme aggregation questions (every `/ask` is scoped to one university/programme).

## Notes
- Out-of-scope and cross-institution-trap questions expect a refusal (`expected_source_ids: []`,
  `should_refuse: true`); they verify the Retrieval Gate / refusal / anti-blending paths, not any fact.
- `country_scope=["all"]` in the current corpus is temporary scaffolding, not final country-aware
  retrieval; gold questions do not encode country-specific expectations.
- In-scope factual questions assume the saved official page covers that topic. The Stuttgart source is
  the German official page and the Saarland source is the official English page. On a small local model
  (`qwen3:1.7b`) some well-supported quick-facts (e.g. a value in an "at a glance" table) may still be
  refused for grounding-recall reasons; the gold encodes the documented ground truth regardless, and a
  stronger generation model is expected to ground them.
