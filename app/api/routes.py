"""API route definitions."""

from typing import Protocol

from fastapi import APIRouter, Depends

from app.api.schemas import (
    AskRequest,
    AskResponse,
    ChecklistRequest,
    ChecklistResponse,
    DetectMissingRequest,
    DetectMissingResponse,
    EmailRequest,
    EmailResponse,
    HealthResponse,
)
from app.core.config import Settings, get_settings
from app.rag.artifacts import (
    REQUIREMENTS_QUERY,
    detect_missing_documents,
    draft_email,
    generate_checklist,
)
from app.rag.generation import (
    DISCLAIMER,
    LLMClient,
    generate_grounded_answer,
    get_llm_client,
)
from app.rag.retrieval import RetrievalResult, retrieve_with_parents

router = APIRouter()


class Retriever(Protocol):
    """Scope-required retrieval callable (Phase 4b ``retrieve_with_parents``)."""

    def __call__(
        self, question: str, *, university_slug: str, programme_slug: str | None = None
    ) -> RetrievalResult: ...


def provide_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    """FastAPI dependency: the configured LLM client (overridden in tests)."""

    return get_llm_client(settings)


def provide_retriever(settings: Settings = Depends(get_settings)) -> Retriever:
    """FastAPI dependency: a retriever bound to settings (overridden in tests)."""

    def _retrieve(
        question: str, *, university_slug: str, programme_slug: str | None = None
    ) -> RetrievalResult:
        return retrieve_with_parents(
            question, university_slug=university_slug, programme_slug=programme_slug
        )

    return _retrieve


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Report service liveness and basic runtime metadata."""

    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        version=settings.api_version,
    )


@router.post("/ask", response_model=AskResponse, tags=["rag"])
def ask(
    request: AskRequest,
    retriever: Retriever = Depends(provide_retriever),
    llm_client: LLMClient = Depends(provide_llm_client),
) -> AskResponse:
    """Answer a question grounded in retrieved official documents, or refuse."""

    retrieval_result = retriever(
        request.question,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
    )
    answer = generate_grounded_answer(
        request.question, retrieval_result, llm_client=llm_client
    )
    return AskResponse(
        answer=answer.answer,
        citations=answer.citations,
        insufficient_context=answer.insufficient_context,
        confidence=answer.confidence,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
        disclaimer=DISCLAIMER,
    )


@router.post("/checklist", response_model=ChecklistResponse, tags=["rag"])
def checklist(
    request: ChecklistRequest,
    retriever: Retriever = Depends(provide_retriever),
    llm_client: LLMClient = Depends(provide_llm_client),
) -> ChecklistResponse:
    """Generate a grounded per-programme application checklist, or refuse."""

    retrieval_result = retriever(
        REQUIREMENTS_QUERY,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
    )
    result = generate_checklist(retrieval_result, llm_client=llm_client)
    return ChecklistResponse(
        items=result.items,
        citations=result.citations,
        insufficient_context=result.insufficient_context,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
        disclaimer=DISCLAIMER,
    )


@router.post("/detect-missing", response_model=DetectMissingResponse, tags=["rag"])
def detect_missing(
    request: DetectMissingRequest,
    retriever: Retriever = Depends(provide_retriever),
    llm_client: LLMClient = Depends(provide_llm_client),
) -> DetectMissingResponse:
    """Compare an applicant profile against retrieved requirements, or refuse."""

    retrieval_result = retriever(
        REQUIREMENTS_QUERY,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
    )
    result = detect_missing_documents(
        request.profile, retrieval_result, llm_client=llm_client
    )
    return DetectMissingResponse(
        missing=result.missing,
        satisfied=result.satisfied,
        citations=result.citations,
        insufficient_context=result.insufficient_context,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
        disclaimer=DISCLAIMER,
    )


@router.post("/draft-email", response_model=EmailResponse, tags=["rag"])
def draft_email_endpoint(
    request: EmailRequest,
    retriever: Retriever = Depends(provide_retriever),
    llm_client: LLMClient = Depends(provide_llm_client),
) -> EmailResponse:
    """Draft a source-anchored formal email to the admissions office, or refuse."""

    retrieval_result = retriever(
        request.topic,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
    )
    result = draft_email(request.topic, retrieval_result, llm_client=llm_client)
    return EmailResponse(
        subject=result.subject,
        body=result.body,
        citations=result.citations,
        insufficient_context=result.insufficient_context,
        university_slug=request.university_slug,
        programme_slug=request.programme_slug,
        disclaimer=DISCLAIMER,
    )
