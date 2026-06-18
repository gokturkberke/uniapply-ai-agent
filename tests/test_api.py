"""Tests for the public API endpoints."""

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    """`/health` returns 200 with the expected status payload."""

    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["app_name"]  # non-empty app name
    assert "environment" in body
    assert "version" in body


def test_health_reports_default_mock_provider() -> None:
    """`/health` reports the active provider; the mock default has no model."""

    body = client.get("/health").json()

    assert body["llm_provider"] == "mock"
    assert body["llm_model"] is None


def test_health_reports_local_provider_and_model() -> None:
    """With the local provider, `/health` echoes the configured model id."""

    app.dependency_overrides[get_settings] = lambda: Settings(
        llm_provider="local_openai", local_llm_model="qwen3:1.7b"
    )
    try:
        body = client.get("/health").json()
    finally:
        app.dependency_overrides.clear()

    assert body["llm_provider"] == "local_openai"
    assert body["llm_model"] == "qwen3:1.7b"
