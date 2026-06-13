"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for the ``/health`` endpoint."""

    status: str = Field(description="Liveness indicator; 'ok' when healthy.")
    app_name: str = Field(description="Human-readable application name.")
    environment: str = Field(description="Active deployment environment.")
    version: str = Field(description="API version identifier.")
