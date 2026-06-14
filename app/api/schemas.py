"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field

from app.rag.generation import Citation


class HealthResponse(BaseModel):
    """Response body for the ``/health`` endpoint."""

    status: str = Field(description="Liveness indicator; 'ok' when healthy.")
    app_name: str = Field(description="Human-readable application name.")
    environment: str = Field(description="Active deployment environment.")
    version: str = Field(description="API version identifier.")


class AskRequest(BaseModel):
    """Request body for the ``/ask`` endpoint."""

    question: str = Field(min_length=1, description="The applicant's question.")
    university_slug: str = Field(
        min_length=1, description="Required scope: the university to answer for."
    )
    programme_slug: str | None = Field(
        default=None, description="Optional scope: a specific programme."
    )


class AskResponse(BaseModel):
    """Grounded answer with citations and the mandatory disclaimer."""

    answer: str
    citations: list[Citation]
    insufficient_context: bool
    confidence: float
    university_slug: str
    programme_slug: str | None
    disclaimer: str
