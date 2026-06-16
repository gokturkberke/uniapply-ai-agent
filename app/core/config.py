"""Application configuration loaded from environment variables / .env file.

Settings are validated by Pydantic and never contain hardcoded secrets.
The LLM layer is local-first: ``mock`` (offline default) or ``local_openai``
(an OpenAI-compatible server such as Ollama / LM Studio).
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables first, then from a local
    ``.env`` file. Unknown keys are ignored so the same ``.env`` can hold
    future (not-yet-wired) variables without breaking startup.
    """

    app_name: str = "UniApply AI Agent"
    environment: str = "development"
    api_version: str = "v1"

    registry_path: str = "data/registry/sources.json"
    raw_dir: str = "data/raw"
    normalized_dir: str = "data/normalized"
    chunk_dir: str = "data/chunks"
    chunk_max_tokens: int = 600
    chunk_overlap_tokens: int = 80

    embedding_provider: str = "fastembed"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_batch_size: int = 32
    qdrant_path: str = "data/index/qdrant"
    qdrant_collection: str = "uniapply_chunks"
    qdrant_url: str | None = None

    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.3

    llm_provider: Literal["mock", "local_openai"] = "mock"
    llm_max_tokens: int = 4096

    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "qwen3:1.7b"
    local_llm_api_key: str = "ollama"
    local_llm_temperature: float | None = None
    local_llm_seed: int | None = None

    eval_gold_path: str = "data/eval/gold.jsonl"
    eval_runs_dir: str = "docs/experiments/runs"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` singleton.

    Caching avoids re-reading the environment/.env on every request and gives
    a single, overridable dependency for FastAPI routes and tests.
    """

    return Settings()
