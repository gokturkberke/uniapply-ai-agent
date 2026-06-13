"""API route definitions."""

from fastapi import APIRouter, Depends

from app.api.schemas import HealthResponse
from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Report service liveness and basic runtime metadata."""

    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        version=settings.api_version,
    )
