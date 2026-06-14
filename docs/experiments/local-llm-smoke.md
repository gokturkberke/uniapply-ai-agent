# Local LLM smoke / demo runbook (laptop-safe)

A short, serial smoke for the `local_openai` provider: prove the app runs end to end on a small local
model (health, two grounded `/ask`, one refusal) without the full eval harness and without heating the
laptop. This is **not** a quality baseline; it proves wiring and grounded-or-refuse behavior only.

See the plan: `docs/experiments/2026-06-14_local-llm-smoke-profile-plan.md`.

## Prerequisites
- Ollama installed and running (`ollama serve`).
- The CS mini-corpus index already built locally (`data/index/qdrant`, gitignored). If missing, build it
  first with `python -m scripts.ingest && python -m scripts.chunk && python -m scripts.index`.

## 1. Pull a small model
```bash
ollama pull qwen3:1.7b      # recommended laptop-safe default
# ollama pull gemma3:1b     # smaller fallback if qwen3:1.7b is still too heavy
# ollama pull llama3.2:3b   # optional comparison
```

## 2. Run the API with the demo profile (one terminal)
```bash
source .venv/bin/activate
LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 uvicorn app.main:app
```
`LLM_MAX_TOKENS=768` keeps generation cheap; raise to `1024` if a small model truncates its JSON.

## 3. Run the probes (serial; one at a time)
Run these one after another. Do **not** fire them in parallel: a parallel local request has produced an
Ollama-side HTTP 500 while serial requests work. All `/ask` probes scope to
`university-of-konstanz` / `msc-computer-and-information-science`. `-w` prints rough latency (the first
`/ask` is cold and includes model load; later calls are warm).

### Probe 1 - health
```bash
curl -s -w "\n time_total=%{time_total}s\n" localhost:8000/health
```
Expect: `status` is `ok`.

### Probe 2 - grounded (eligibility / points system)
```bash
curl -s -w "\n time_total=%{time_total}s\n" localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "Does the University of Konstanz admission committee decide eligibility using the application documents and a points system?", "university_slug": "university-of-konstanz", "programme_slug": "msc-computer-and-information-science"}'
```

### Probe 3 - grounded (uni-assist timing)
```bash
curl -s -w "\n time_total=%{time_total}s\n" localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "How early does uni-assist recommend applying before the deadline?", "university_slug": "university-of-konstanz", "programme_slug": "msc-computer-and-information-science"}'
```

### Probe 4 - unsupported (refusal)
```bash
curl -s -w "\n time_total=%{time_total}s\n" localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is the tuition fee for an MBA at Harvard Business School?", "university_slug": "university-of-konstanz", "programme_slug": "msc-computer-and-information-science"}'
```

## What to check (assertion contract: shape only, never the answer text)
- **Probes 2-3 (grounded):** HTTP 200, `insufficient_context == false`, `len(citations) >= 1`, and the
  cited `source_id` is in the Konstanz scope (probe 2 likely `konstanz-cis-official-programme-page`;
  probe 3 likely `uni-assist-processing-time-konstanz-cis`). The `answer` text may be printed for human
  inspection but is **not** asserted as a fact.
- **Probe 4 (refusal):** HTTP 200, `answer == "Information not found in the official documents."` (the
  only verbatim text assertion), `insufficient_context == true`, `citations == []`.

## Notes
- Grounded probes assert response **shape only**; only the refusal string is asserted verbatim. These
  probes are demo questions kept separate from the gitignored gold set (eval-set isolation) and assert
  no admission facts.
- A JSON/schema-validation failure (including `LLM_MAX_TOKENS` truncation) makes the provider fall back
  to the safe grounded refusal. Record that as a **smoke result, not a product bug**; if a grounded probe
  refuses only because of truncation, raise `LLM_MAX_TOKENS` to `1024` and re-run that probe.
- Record latency roughly (cold vs warm). Do not optimize here - performance tuning is separate work.
- This runbook does not run `scripts.evaluate`; the full 12-question eval/judge baseline is out of scope.
- Verified run (`qwen3:1.7b`, `LLM_MAX_TOKENS=768`, serial): all four probes passed; ~4.5-7.5 s per
  answer (vs ~55-75 s for `qwen3:4b`). Full per-probe results are recorded in
  `docs/experiments/2026-06-14_local-llm-smoke-profile-plan.md` (Item 4).
- Known observation (not a blocker): a citation's `source_id` is correct, but its `heading_path` may
  arrive as a single `">"`-joined string instead of a list of components. Grounding is `source_id`-based,
  so this does not affect the smoke; it is a candidate future citation-polish item.
