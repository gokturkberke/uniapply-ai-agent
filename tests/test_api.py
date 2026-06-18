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


def test_programmes_lists_registry_programmes() -> None:
    """`/programmes` returns the distinct programmes from the committed registry."""

    response = client.get("/programmes")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    keys = {(p["university_slug"], p["programme_slug"]) for p in body}
    assert ("university-of-konstanz", "msc-computer-and-information-science") in keys
    assert all(p["title"] for p in body)  # every programme has a display title

    konstanz = next(p for p in body if p["university_slug"] == "university-of-konstanz")
    assert konstanz["title"] == "University of Konstanz - M.Sc. Computer and Information Science"
