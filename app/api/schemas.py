"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field

from app.rag.artifacts import ChecklistItem
from app.rag.generation import Citation


class HealthResponse(BaseModel):
    """Response body for the ``/health`` endpoint."""

    status: str = Field(description="Liveness indicator; 'ok' when healthy.")
    app_name: str = Field(description="Human-readable application name.")
    environment: str = Field(description="Active deployment environment.")
    version: str = Field(description="API version identifier.")
    llm_provider: str = Field(description="Active LLM provider ('mock' or 'local_openai').")
    llm_model: str | None = Field(
        default=None,
        description="Active local model id, or null when the provider is 'mock'.",
    )


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


class ChecklistRequest(BaseModel):
    """Request body for ``/checklist`` (per-programme)."""

    university_slug: str = Field(min_length=1)
    programme_slug: str = Field(min_length=1)


class ChecklistResponse(BaseModel):
    """A grounded per-programme application checklist."""

    items: list[ChecklistItem]
    citations: list[Citation]
    insufficient_context: bool
    university_slug: str
    programme_slug: str
    disclaimer: str


class DetectMissingRequest(BaseModel):
    """Request body for ``/detect-missing``."""

    university_slug: str = Field(min_length=1)
    programme_slug: str = Field(min_length=1)
    profile: list[str] = Field(
        default_factory=list,
        description="Documents/credentials the applicant already has.",
    )


class DetectMissingResponse(BaseModel):
    """Required items split into missing vs satisfied for an applicant profile."""

    missing: list[str]
    satisfied: list[str]
    citations: list[Citation]
    insufficient_context: bool
    university_slug: str
    programme_slug: str
    disclaimer: str


class EmailRequest(BaseModel):
    """Request body for ``/draft-email``."""

    university_slug: str = Field(min_length=1)
    programme_slug: str | None = None
    topic: str = Field(min_length=1, description="What the email should ask or state.")


class EmailResponse(BaseModel):
    """A source-anchored formal email draft to the admissions office."""

    subject: str
    body: str
    citations: list[Citation]
    insufficient_context: bool
    university_slug: str
    programme_slug: str | None
    disclaimer: str
