**Date:** 2026-06-16
**Topic:** Dockerized backend (infra milestone) - containerize the FastAPI RAG API + Qdrant server service
**Motivation:** The backend runs today as a local venv (`uvicorn app.main:app`) with embedded on-disk
Qdrant (`QdrantClient(path=data/index/qdrant)`) and host-side Ollama. This milestone adds
deployment/reproducibility via Docker (a learning goal toward an eventual frontend), without expanding
RAG scope. It containerizes the API, runs Qdrant as a **server service**, and keeps the local dev flow
unchanged (Docker is additive/optional).
**Hypothesis:** The existing API runs unchanged in Docker with a Qdrant server (selected by a new opt-in
`qdrant_url`) and host Ollama via `host.docker.internal`, preserving local dev, the offline test suite,
and the grounding-or-refuse guarantee - with **one small additive code change** (`qdrant_url`) and **no
new dependency**.
**Preconditions:** V1 + local-LLM work merged to `main`; working tree clean; Docker Engine + Compose
available on the host; Ollama running on the host for any local-LLM smoke.

This is an **infra slice**: no frontend, no new RAG features, no endpoint/schema changes, no model
experiments. The product guarantee is unchanged: unsupported scoped questions return exactly
`Information not found in the official documents.`

---

## 1) `qdrant_url` support (the only code change)
- **Goal:** Let Docker use a Qdrant **server** while local dev keeps embedded on-disk Qdrant; opt-in,
  default behavior unchanged when unset.
- **Files:** `app/core/config.py`, `app/rag/vector_store.py` (`from_settings`), `.env.example`,
  `tests/test_vector_store.py`.
- **Steps:** add `qdrant_url: str | None = None`; in `from_settings()` insert
  `elif settings.qdrant_url: QdrantClient(url=settings.qdrant_url)` between the `location` (test) and the
  embedded `path` branches; document `QDRANT_URL=` in `.env.example`; add an offline test that
  `Settings(qdrant_url=...)` selects the url branch (no live server).
- **Test / verification:** `pytest` green and offline (existing `:memory:` tests untouched; they bypass
  `from_settings()` so a present `QDRANT_URL` cannot affect them).
- **Expected outcome:** embedded mode byte-identical when `qdrant_url` unset; server mode used when set.
- **DONE / DROPPED:**

## 2) `Dockerfile` (API image)
- **Goal:** A small, reproducible image for the FastAPI app.
- **Files:** `Dockerfile`.
- **Steps:** `python:3.12-slim`; `apt-get install --no-install-recommends libgomp1 curl` (libgomp1 is
  required: fastembed -> onnxruntime -> OpenMP); copy `requirements.txt` first + `pip install` (layer
  caching), then `app/` + `scripts/` + committed `data/registry/`; `ENV FASTEMBED_CACHE_PATH=/cache/fastembed`;
  non-root user; `EXPOSE 8000`; `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`; optional HEALTHCHECK on `/health`.
- **Test / verification:** `docker compose build` (user-run); image starts and serves `/health`.
- **Expected outcome:** a working API image with no model re-download (cache volume) and no missing OpenMP.
- **DONE / DROPPED:**

## 3) `.dockerignore`
- **Goal:** Keep secrets/data/caches out of the build context.
- **Files:** `.dockerignore`.
- **Steps:** exclude `.git`, `.venv`/`venv`, `__pycache__`/`*.pyc`, `.pytest_cache`/`.mypy_cache`/`.ruff_cache`,
  `.env`/`.env.*`, `docs/experiments/runs/`, and `data/raw|normalized|chunks|index|eval`. **Keep
  `data/registry/`** (committed manifest baked into the image; bind-mount overlays at runtime).
- **Test / verification:** build context excludes the above; image does not contain `.env` or data artifacts.
- **DONE / DROPPED:**

## 4) `docker-compose.yml`
- **Goal:** Orchestrate `api` + `qdrant` with persistent + cache volumes and host-Ollama reachability.
- **Files:** `docker-compose.yml`.
- **Steps:** `api` (build `.`, `8000:8000`, `depends_on: qdrant`, `env_file: .env`, `environment:`
  overriding `QDRANT_URL=http://qdrant:6333` + `LOCAL_LLM_BASE_URL=http://host.docker.internal:11434/v1`,
  `extra_hosts: host.docker.internal:host-gateway`, volumes `./data:/app/data` + `fastembed_cache:/cache/fastembed`);
  `qdrant` (`qdrant/qdrant`, `6333:6333`, volume `qdrant_storage:/qdrant/storage`); named volumes
  `qdrant_storage`, `fastembed_cache`.
- **Test / verification:** `docker compose config` parses (CI-style syntax check); `docker compose up --build`
  + `curl localhost:8000/health` (user-run).
- **Expected outcome:** API talks to the qdrant server; the Docker index lives in `qdrant_storage`
  (separate from the local embedded index - rebuild once per mode).
- **DONE / DROPPED:**

## 5) `Makefile`
- **Goal:** Ergonomic Docker commands.
- **Files:** `Makefile`.
- **Steps:** `docker-up`, `docker-down`, `docker-build`, `docker-shell`, `docker-test`
  (`docker compose run --rm api pytest`), and `docker-ingest`/`docker-chunk`/`docker-index`/`docker-evaluate`
  (`docker compose run --rm api python -m scripts.<name>`).
- **Test / verification:** `make -n docker-test` etc. expand to the expected commands.
- **DONE / DROPPED:**

## 6) Docs: `docs/docker.md` + README quickstart
- **Goal:** Make the Docker flow runnable + clear that it is optional.
- **Files:** `docs/docker.md` (new), `README.md` (add a short Docker quickstart).
- **Steps:** docker.md covers first-time setup (`cp .env.example .env`), embedded-vs-server Qdrant (and the
  rebuild-index-per-mode note), host Ollama via `host.docker.internal`, building the index in Docker, an
  optional `EMBEDDING_PROVIDER=fake` no-download smoke, and troubleshooting; README gets a short Docker
  quickstart stating Docker is additive, not a replacement for local dev.
- **Test / verification:** docs are accurate vs the compose/Makefile; links resolve.
- **DONE / DROPPED:**

## Non-goals
- No frontend; no new RAG features/endpoints/schemas; no model experiments; no change to the default
  `LLM_PROVIDER`. Ollama stays on the host (not containerized). No new Python dependency.
- **Never committed:** `.env`, `data/raw|normalized|chunks|index|eval`, the gold set, eval reports, API keys.

## Git / workflow
- Branch `infra/dockerized-backend` (never push `main`). Commit order: AGENTS.md sync -> this plan file ->
  `qdrant_url` code -> Docker/compose/Makefile/docs -> DONE markers; `pytest` green; push + PR.

## Files touched
- New: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `Makefile`, `docs/docker.md`,
  `docs/experiments/2026-06-16_dockerized-backend-plan.md`.
- Edited: `app/core/config.py`, `app/rag/vector_store.py`, `.env.example`, `tests/test_vector_store.py`,
  `README.md`, `AGENTS.md` (status sync). No new dependency.
