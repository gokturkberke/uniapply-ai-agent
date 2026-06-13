"""FastAPI application entry point.

Run locally with::

    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "RAG-based university application assistant for international "
            "Master's applicants. (Scaffold — RAG features coming soon.)"
        ),
        version=settings.api_version,
    )
    app.include_router(router)
    return app


app = create_app()
