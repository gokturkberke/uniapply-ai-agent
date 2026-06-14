# Evaluation Gold Set — Summary (structure only)

This is a **fact-free** structural summary of the evaluation gold set. The gold set itself
(`data/eval/gold.jsonl`) is **gitignored** and kept isolated from any tuning/few-shot data. This
document deliberately contains **no question answers and no admission facts** (deadlines, fees,
language requirements, required documents, eligibility) — only counts, categories, scopes, and the
`source_id`s the questions are expected to retrieve from.

## Totals
- Questions: **12**
- `should_refuse: true`: **2** (the out-of-scope questions)

## By category
| category | count |
|---|---|
| factual | 6 |
| multi_hop | 3 |
| reformulation | 1 |
| out_of_scope | 2 |

## By scope (university_slug / programme_slug)
| scope | count |
|---|---|
| university-of-konstanz / msc-computer-and-information-science | 6 |
| paderborn-university / msc-computer-science | 6 |

## Referenced source_ids (expected retrieval targets)
- `konstanz-cis-official-programme-page`
- `uni-assist-vpd-konstanz-cis`
- `uni-assist-processing-time-konstanz-cis`
- `paderborn-cs-official-programme-page`
- `uni-assist-vpd-paderborn-cs`
- `uni-assist-processing-time-paderborn-cs`

(All six sources in the committed Computer Science mini-corpus registry are exercised.)

## Notes
- Out-of-scope questions expect a refusal (`expected_source_ids: []`, `should_refuse: true`); they
  verify the Retrieval Gate / refusal path, not any fact.
- `country_scope=["all"]` in the current corpus is temporary scaffolding, not final country-aware
  retrieval; gold questions do not encode country-specific expectations.
- In-scope factual questions assume the saved official page actually covers that topic. If a page
  does not, the system will (correctly) refuse and the question should be pruned/adjusted rather than
  asserting a fact not present in the corpus.
