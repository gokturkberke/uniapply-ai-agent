# UniApply AI Agent

A RAG-based university application assistant for **international Master's
applicants**. UniApply ingests university admission documents and helps
applicants navigate the process end to end.

> **Status:** early scaffold. This repository currently ships a clean,
> testable FastAPI skeleton with a `/health` endpoint. RAG, LLM integration,
> and agent orchestration are planned (see [Roadmap](#roadmap)).

## Project Goal

Reduce the friction and uncertainty of applying to Master's programs abroad by
turning dense, inconsistent admission documents into trustworthy, cited answers
and ready-to-use application artifacts.

## Planned Features

- **Document-grounded Q&A with citations** — answer applicant questions using
  retrieval over ingested admission documents, always citing the source.
- **Application checklist generation** — produce per-program checklists
  (deadlines, required documents, language tests, fees) from the source material.
- **Formal email drafting** — draft polished, formal emails to admissions
  offices (inquiries, document submission, deadline clarifications).

## Architecture Overview

**Today (this scaffold):**

```
app/
├── main.py          # FastAPI app factory (create_app) + router wiring
├── api/
│   ├── routes.py    # HTTP endpoints (currently: /health)
│   └── schemas.py   # Pydantic request/response models
└── core/
    └── config.py    # Settings via pydantic-settings (env / .env)
tests/
└── test_api.py      # /health endpoint test (FastAPI TestClient)
```

- **FastAPI** serves the HTTP API; the app is built by a `create_app()` factory.
- **Pydantic / pydantic-settings** handle validation and configuration. No
  secrets are hardcoded — all configuration comes from environment variables
  (loaded from `.env` locally).
- **pytest** drives tests against the app via `TestClient`.

**Planned layers (not yet implemented):**

- **Ingestion**: parse and chunk admission documents (PDF/HTML).
- **Retrieval (RAG)**: embeddings + a vector store for semantic search.
- **LLM layer**: grounded generation with citations (Anthropic / OpenAI).
- **Agent orchestration**: LangGraph for multi-step flows (checklists, emails).

## Requirements

- Python **3.12**

## Setup

```bash
# 1. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your local environment file
cp .env.example .env               # then edit values as needed
```

## Running the API

```bash
uvicorn app.main:app --reload
```

Then visit:

- Health check: <http://localhost:8000/health>
- Interactive docs (Swagger UI): <http://localhost:8000/docs>

Example:

```bash
curl http://localhost:8000/health
# {"status":"ok","app_name":"UniApply AI Agent","environment":"development","version":"v1"}
```

## Running Tests

```bash
pytest
```

## Roadmap

- [x] FastAPI scaffold + `/health`
- [ ] Document ingestion pipeline
- [ ] Vector store + retrieval
- [ ] Grounded Q&A with citations
- [ ] Checklist generation
- [ ] Admissions email drafting
- [ ] LangGraph agent orchestration

## Configuration

All configuration is read from environment variables (or a local `.env`).
See [`.env.example`](.env.example) for available settings. **Never commit a
real `.env` or any API keys.**
