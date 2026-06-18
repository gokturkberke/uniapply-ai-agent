.PHONY: run-local docker-build docker-up docker-down docker-shell docker-test \
        docker-ingest docker-chunk docker-index docker-evaluate

# Run the API locally against host Ollama (real grounded answers, not the mock
# stub). Deterministic sampling for a stable demo. Requires `ollama pull qwen3:1.7b`.
run-local:
	LLM_PROVIDER=local_openai LOCAL_LLM_MODEL=qwen3:1.7b LLM_MAX_TOKENS=1536 \
	  LOCAL_LLM_TEMPERATURE=0 LOCAL_LLM_SEED=42 uvicorn app.main:app --reload

# Build the API image.
docker-build:
	docker compose build

# Start api + qdrant (rebuilds if needed); Ctrl-C to stop.
docker-up:
	docker compose up --build

# Stop and remove the services (named volumes are kept).
docker-down:
	docker compose down

# Open a shell in a throwaway api container.
docker-shell:
	docker compose run --rm api bash

# Run the offline test suite in the api container (no qdrant service needed).
docker-test:
	docker compose run --rm --no-deps api pytest

# Pipeline (writes raw/normalized/chunks via the ./data bind-mount; index -> qdrant service).
docker-ingest:
	docker compose run --rm api python -m scripts.ingest

docker-chunk:
	docker compose run --rm api python -m scripts.chunk

docker-index:
	docker compose run --rm api python -m scripts.index

docker-evaluate:
	docker compose run --rm api python -m scripts.evaluate --run-label docker
