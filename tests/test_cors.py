"""Tests for browser CORS support on the API."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)

ALLOWED_ORIGIN = "http://localhost:5173"


def test_cors_allows_configured_origin() -> None:
    """A simple request from an allowed origin echoes that origin back."""

    response = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_cors_preflight_allows_post() -> None:
    """A preflight for POST /ask from an allowed origin is permitted."""

    response = client.options(
        "/ask",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_cors_rejects_unknown_origin() -> None:
    """An origin outside the allow list is not granted the CORS header."""

    response = client.get(
        "/health", headers={"Origin": "http://evil.example.com"}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_default_cors_origins_include_vite_dev_server() -> None:
    """The default configuration permits the Vite dev origins."""

    origins = get_settings().cors_allow_origins_list

    assert ALLOWED_ORIGIN in origins
    assert "http://127.0.0.1:5173" in origins
