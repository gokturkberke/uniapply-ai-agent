# Running UniApply with Docker

Docker is **optional and additive** — it does not replace the local venv flow in the README. It runs the
**full stack** — the FastAPI API, **Qdrant as a server service**, and the **frontend** — which is closer to a
real deployment and avoids the embedded single-process file lock.

## What runs where
- **`api`** container — the FastAPI app (`uvicorn app.main:app`).
- **`qdrant`** container — the official Qdrant server; the Docker index lives in its `qdrant_storage` volume.
- **`frontend`** container — nginx serving the built SPA on `http://localhost:8080`; it reverse-proxies
  `/api/*` to the `api` service, so the browser uses a single origin and needs no CORS.
- **Ollama stays on your host** (not containerized); the `api` container reaches it at
  `http://host.docker.internal:11434/v1`.

> Embedded vs server Qdrant: local dev uses **embedded on-disk** Qdrant (`data/index/qdrant`); Docker uses
> the **server** (`QDRANT_URL=http://qdrant:6333`). These are **separate stores** — you build the index
> once per mode. Switching to Docker does not reuse your local `data/index`.

## First-time setup
```bash
cp .env.example .env          # required: docker-compose reads .env
docker compose up --build     # or: make docker-up
# UI:  http://localhost:8080
curl localhost:8000/health    # {"status":"ok", ...}
```
Compose overrides two values for the container regardless of your `.env`: `QDRANT_URL=http://qdrant:6333`
and `LOCAL_LLM_BASE_URL=http://host.docker.internal:11434/v1`.

## Frontend (full stack)
`docker compose up --build` also serves the **frontend** at <http://localhost:8080>. nginx serves the static
SPA and reverse-proxies `/api/*` to the `api` service over the compose network, so the browser stays on a
**single origin** — no CORS in Docker (local Vite dev on `:5173` still uses the CORS allow-list). The image
bakes `VITE_API_BASE_URL=/api` at build time, and the `frontend` service waits for the `api` healthcheck
before starting, so it never proxies to a dead upstream. For real answers, set `LLM_PROVIDER=local_openai` in
`.env`; the header provider chip shows mock vs the active model.

## Build the index inside Docker
The image ships only the committed `data/registry/`; raw documents and the index are not baked in. With
your raw pages saved under `./data/raw/` (bind-mounted into the container):
```bash
make docker-ingest    # raw -> data/normalized (bind-mount)
make docker-chunk     # -> data/chunks (bind-mount)
make docker-index     # embed -> qdrant service (qdrant_storage volume)
```
The first `docker-index` downloads the embedding model into the `fastembed_cache` volume (set via
`FASTEMBED_CACHE_PATH`), so it is not re-downloaded on later runs. For a fast no-download smoke, set
`EMBEDDING_PROVIDER=fake` in `.env` (deterministic hash embeddings; not for real answers).

## Using a local LLM (host Ollama)
In `.env` set `LLM_PROVIDER=local_openai` and `LOCAL_LLM_MODEL=qwen3:1.7b` (compose supplies the
host-reachable base URL). Then `/ask` answers via your host Ollama. With `LLM_PROVIDER=mock` (the default)
the API runs fully offline.

## Tests
```bash
make docker-test      # docker compose run --rm --no-deps api pytest
```
The suite is fully offline (in-memory Qdrant + mocked LLM/HTTP), so it needs **no** qdrant service.

## Make targets
`docker-build`, `docker-up`, `docker-down`, `docker-shell`, `docker-test`, `docker-ingest`,
`docker-chunk`, `docker-index`, `docker-evaluate`.

## Troubleshooting
- **`docker compose` errors about `.env`** — run `cp .env.example .env` first.
- **UI at :8080 loads but API calls fail (502)** — nginx proxies `/api/*` to the `api` service; a 502 means
  api is not healthy yet. Check `docker compose ps` and api logs. `curl localhost:8080/api/health` should
  mirror `curl localhost:8000/health`.
- **`/ask` always refuses / empty results** — the Docker (server) index is empty until you run
  `make docker-ingest && make docker-chunk && make docker-index`; it is separate from your local index.
- **Missing raw files** — ingestion needs the official pages under `./data/raw/` (gitignored); save them first.
- **Qdrant connection errors** — ensure the `qdrant` service is up (`docker compose ps`); the API connects
  lazily, so a not-yet-ready Qdrant only fails on index/retrieval, not at boot.
- **Qdrant client/server version warning** — harmless soft warning; pin `qdrant/qdrant:<version>` in
  `docker-compose.yml` to silence it.
- **Local model unreachable** — confirm `ollama serve` is running on the host and the model is pulled;
  on Linux the `host.docker.internal:host-gateway` mapping (already in compose) is what makes it reachable.
- **Permission denied writing `./data` (Linux)** — the container runs as uid 1000; ensure `./data` is
  writable by that uid (e.g. `chmod`/`chown`), or run the pipeline locally and only serve from Docker.
