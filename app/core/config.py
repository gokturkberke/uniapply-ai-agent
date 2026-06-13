"""Application configuration loaded from environment variables / .env file.

Settings are validated by Pydantic and never contain hardcoded secrets.
Future RAG/LLM credentials (e.g. ANTHROPIC_API_KEY) will be added here as
optional fields once those features land.
"""

from functools import lru_cache

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
