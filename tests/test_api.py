"""Tests for the public API endpoints."""

from fastapi.testclient import TestClient

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
