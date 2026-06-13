# CLAUDE.md — Project Rules & Development Instructions

Guidance for Claude Code (and humans) working in this repository.

## What this project is

UniApply AI Agent is a RAG-based university application assistant for
international Master's applicants. See `README.md` for goals and roadmap.

**Current state:** a minimal, clean FastAPI scaffold with a `/health`
endpoint. RAG and agent orchestration are **not** implemented yet.

## Tech stack (do not deviate without being asked)

- **Python 3.12**
- **FastAPI** for the HTTP API
- **Pydantic** + **pydantic-settings** for models and configuration
- **python-dotenv** / pydantic-settings for `.env` loading
- **pytest** (+ `httpx` via `TestClient`) for tests

## Core rules

- **Never hardcode API keys or secrets.** All configuration comes from
  environment variables, surfaced through `app/core/config.py`
  (`Settings` / `get_settings`). Add new config as typed fields there.
- **Always add type hints** to function signatures and return types.
- **Keep functions small and readable** — one clear responsibility each.
- **Use Pydantic models** for all request/response bodies (in
  `app/api/schemas.py`), not raw dicts.
- **Add/maintain tests** for new endpoints and behavior in `tests/`.
- **Run the tests before considering a change done** (`pytest`).
- **Do not add RAG or LangGraph** until that work is explicitly requested;
  keep the scaffold simple.

## Project layout

```
app/
├── main.py          # create_app() factory; module-level `app` for uvicorn
├── api/
│   ├── routes.py    # APIRouter endpoints
│   └── schemas.py   # Pydantic request/response models
└── core/
    └── config.py    # Settings (env / .env), get_settings()
tests/
└── test_api.py      # endpoint tests via FastAPI TestClient
```

### Conventions

- Register new routes on the `APIRouter` in `app/api/routes.py`; they are wired
  into the app by `create_app()` in `app/main.py`.
- Inject settings via `Depends(get_settings)` rather than reading env vars
  directly inside handlers (keeps handlers testable and overridable).
- Imports use the `app.` package root (e.g. `from app.core.config import ...`).

## Development commands

```bash
# Set up environment (first time)
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Run the API (auto-reload)
uvicorn app.main:app --reload

# Run the tests
pytest
```

## Definition of done for a change

1. Type hints present; functions small and focused.
2. No secrets committed; new config goes through `Settings`.
3. Tests added/updated and `pytest` passes.
4. `README.md` / this file updated if behavior or setup changed.
