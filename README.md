# UniApply AI Agent

A RAG-based university application assistant for **international Master's applicants**. UniApply ingests
official university admission documents and answers applicant questions with **source citations**,
generates per-programme application artifacts, and never fabricates admission facts.

> **Status:** V1 RAG pipeline implemented end to end (ingest -> retrieve -> grounded-or-refuse answering
> with citations), exposed over FastAPI, with an in-repo evaluation harness. LangGraph-style agent
> orchestration is not implemented.

## Core guarantee

Answers are **grounded in the ingested documents and cite their sources**. When the scoped documents do
not support an answer, the API refuses with exactly `Information not found in the official documents.`
rather than guessing. Retrieval is **strictly scoped to one university/programme** so facts are never
blended across institutions.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + runtime metadata |
| POST | `/ask` | Grounded Q&A with citations (or refusal) |
| POST | `/checklist` | Per-programme application checklist |
| POST | `/detect-missing` | Compare an applicant profile vs the programme's required documents |
| POST | `/draft-email` | Draft a source-anchored email to the admissions office |

Every `/ask`-style request is scoped by `university_slug` (+ optional `programme_slug`); responses carry
`citations`, an `insufficient_context` flag, and a mandatory disclaimer.

## Architecture

```
app/                     # thin FastAPI delivery layer
├── main.py              # create_app() factory + router wiring
├── api/{routes,schemas} # endpoints + Pydantic request/response models
└── core/config.py       # typed Settings (pydantic-settings, env / .env)
app/rag/                 # domain pipeline (kept out of the delivery layer)
├── registry.py          # curated source manifest loader + scope filters
├── metadata.py          # source/chunk contracts (slug-validated scoping)
├── parsers.py, ingestion.py   # raw PDF/HTML -> normalized Markdown
├── chunking.py, parents.py    # structure-aware chunks + parent sections
├── embeddings.py, vector_store.py, indexing.py  # fastembed + local Qdrant
├── retrieval.py         # scope-required dense retrieval + Retrieval Gate
├── generation.py        # LLM clients + grounded-or-refuse answering
├── artifacts.py         # checklist / missing-docs / email generators
└── evaluation.py        # in-repo eval metrics + LLM-judge faithfulness
scripts/                 # ingest | chunk | index | search | evaluate (CLI)
tests/                   # pytest, fully offline (MockLLM + httpx.MockTransport)
data/                    # registry (committed); raw/normalized/chunks/index/eval (gitignored)
docs/experiments/        # project memory: every plan + its outcome
```

## LLM providers

Selected by `LLM_PROVIDER` (see `.env.example`):

- `mock` — deterministic, no network; used by the test suite and wiring smokes.
- `anthropic` — Anthropic Claude via the official SDK (needs `ANTHROPIC_API_KEY`).
- `local_openai` — any OpenAI-compatible local server (Ollama / LM Studio); free, no key.

Structured output is validated against Pydantic models; if a local model returns unparseable output the
client falls back to a grounded refusal rather than guessing. Mock and Anthropic paths are unaffected.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit values as needed
```

## Running the API

```bash
uvicorn app.main:app --reload
```

- Health: <http://localhost:8000/health>  ·  Swagger UI: <http://localhost:8000/docs>

```bash
curl -s localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"question": "What documents are required to apply?",
       "university_slug": "university-of-konstanz",
       "programme_slug": "msc-computer-and-information-science"}'
```

### Local LLM (free, no API key)

Run a small local model via [Ollama](https://ollama.com) — `qwen3:1.7b` is the recommended laptop-safe
default. For stable (deterministic) local runs, pin sampling:

```bash
ollama pull qwen3:1.7b
LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=768 \
  LOCAL_LLM_TEMPERATURE=0 LOCAL_LLM_SEED=42 uvicorn app.main:app
```

A copy-pasteable smoke runbook lives at [`docs/experiments/local-llm-smoke.md`](docs/experiments/local-llm-smoke.md).

## Corpus & pipeline

The corpus is driven by a committed manifest (`data/registry/sources.json`) of official sources; the
documents and built indexes themselves are **gitignored**. Build the index, then query or evaluate:

```bash
python -m scripts.ingest      # raw PDF/HTML -> normalized Markdown
python -m scripts.chunk       # structure-aware chunks + parent sections
python -m scripts.index       # embed + write the local Qdrant index
python -m scripts.search "application deadline" --university university-of-konstanz --programme msc-computer-and-information-science
```

## Evaluation

```bash
python -m scripts.evaluate --run-label baseline
```

Replays a gitignored gold set through retrieval + grounded generation and scores retrieval recall,
citation recall/grounding, refusal accuracy, and LLM-judged faithfulness. Reports are written under
`docs/experiments/runs/<label>/` (gitignored).

## Tests

```bash
pytest
```

Fully offline (no network, no API key): `MockLLMClient` and `httpx.MockTransport` stand in for real providers.

## Configuration

All configuration is read from environment variables (or a local `.env`); see
[`.env.example`](.env.example) for every available setting. Never commit a real `.env` or any API keys.
