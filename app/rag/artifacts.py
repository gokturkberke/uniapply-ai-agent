"""Grounded artifact generation: application checklist, missing-document detection,
and source-anchored admissions email.

Each artifact reuses the Phase 5 grounded pattern (``app.rag.generation``): refuse
without an LLM call when there is no grounding context, build a grounded prompt from
the retrieved parent sections, generate a validated structured output, normalize a
model-reported ``insufficient_context`` to the canonical refusal, and drop citations
that fall outside the retrieved context. Answers use ONLY the retrieved context.
"""

from pydantic import BaseModel

from app.rag.generation import (
    Citation,
    LLMClient,
    format_context,
    ground_citations,
    is_groundable,
    safe_generate,
)
from app.rag.retrieval import RetrievalResult

# Canned retrieval query for requirement-centric artifacts (checklist, detect-missing).
REQUIREMENTS_QUERY = (
    "application requirements, required documents, deadlines, language requirements, "
    "and application steps"
)


class ChecklistItem(BaseModel):
    requirement: str
    detail: str


class Checklist(BaseModel):
    items: list[ChecklistItem]
    citations: list[Citation]
    insufficient_context: bool


class MissingDocsResult(BaseModel):
    missing: list[str]
    satisfied: list[str]
    citations: list[Citation]
    insufficient_context: bool


class EmailDraft(BaseModel):
    subject: str
    body: str
    citations: list[Citation]
    insufficient_context: bool


_CONTRACT = (
    "Use ONLY the provided context from official admission documents. Do not use outside "
    "or prior knowledge. Prefer primary university sources over secondary ones (uni-assist, "
    "DAAD) when they conflict. If the context lacks enough information, set "
    "insufficient_context to true. Do not infer eligibility, outcomes, or legal "
    "certainties. Cite only sources present in the context, by their source id."
)


def _checklist_refusal() -> Checklist:
    return Checklist(items=[], citations=[], insufficient_context=True)


def _missing_refusal() -> MissingDocsResult:
    return MissingDocsResult(
        missing=[], satisfied=[], citations=[], insufficient_context=True
    )


def _email_refusal() -> EmailDraft:
    return EmailDraft(subject="", body="", citations=[], insufficient_context=True)


def generate_checklist(
    retrieval_result: RetrievalResult, *, llm_client: LLMClient
) -> Checklist:
    """Produce a grounded per-programme application checklist, or refuse."""

    if not is_groundable(retrieval_result):
        return _checklist_refusal()

    system = (
        "You are UniApply. Extract the application checklist (required documents, "
        "deadlines, language requirements, and application steps) for the programme.\n"
        + _CONTRACT
    )
    user = f"Context:\n{format_context(retrieval_result)}"
    result = safe_generate(
        llm_client, system=system, user=user, output_model=Checklist, fallback=_checklist_refusal()
    )

    grounded = ground_citations(result.citations, retrieval_result)
    if result.insufficient_context or not grounded:
        return _checklist_refusal()
    return result.model_copy(update={"citations": grounded})


def detect_missing_documents(
    profile: list[str], retrieval_result: RetrievalResult, *, llm_client: LLMClient
) -> MissingDocsResult:
    """Compare an applicant profile against retrieved requirements, or refuse."""

    if not is_groundable(retrieval_result):
        return _missing_refusal()

    system = (
        "You are UniApply. From the context, determine the required documents/credentials "
        "for the programme. Compare them against the applicant's profile (items they "
        "already have). Return which required items are still missing and which are "
        "satisfied.\n" + _CONTRACT
    )
    profile_text = "\n".join(f"- {item}" for item in profile) or "(none provided)"
    user = (
        f"Applicant profile (already have):\n{profile_text}\n\n"
        f"Context:\n{format_context(retrieval_result)}"
    )
    result = safe_generate(
        llm_client,
        system=system,
        user=user,
        output_model=MissingDocsResult,
        fallback=_missing_refusal(),
    )

    grounded = ground_citations(result.citations, retrieval_result)
    if result.insufficient_context or not grounded:
        return _missing_refusal()
    return result.model_copy(update={"citations": grounded})


def draft_email(
    topic: str, retrieval_result: RetrievalResult, *, llm_client: LLMClient
) -> EmailDraft:
    """Draft a formal, source-anchored email to the admissions office, or refuse."""

    if not is_groundable(retrieval_result):
        return _email_refusal()

    system = (
        "You are UniApply. Draft a concise, formal email from an applicant to the "
        "admissions office about the given topic. Anchor every factual statement in the "
        "provided context and cite its source.\n" + _CONTRACT
    )
    user = f"Email topic:\n{topic}\n\nContext:\n{format_context(retrieval_result)}"
    result = safe_generate(
        llm_client, system=system, user=user, output_model=EmailDraft, fallback=_email_refusal()
    )

    grounded = ground_citations(result.citations, retrieval_result)
    if result.insufficient_context or not grounded:
        return _email_refusal()
    return result.model_copy(update={"citations": grounded})
