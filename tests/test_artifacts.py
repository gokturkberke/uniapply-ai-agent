"""Tests for the artifact services (offline, MockLLM)."""

from app.rag.artifacts import (
    Checklist,
    ChecklistItem,
    EmailDraft,
    MissingDocsResult,
    detect_missing_documents,
    draft_email,
    generate_checklist,
)
from app.rag.generation import Citation, MockLLMClient
from app.rag.metadata import Chunk, Language, ParentSection, SourceAuthority
from app.rag.retrieval import RetrievalResult, RetrievedChunk

SOURCE_ID = "alpha-src"


class _BoomLLM:
    def generate(self, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("LLM must not be called when context is insufficient")


def _result(*, sufficient: bool, with_parents: bool = True) -> RetrievalResult:
    parent = ParentSection(
        parent_id=f"{SOURCE_ID}::section::000",
        source_id=SOURCE_ID,
        heading_path=["Required Documents"],
        text="Transcript, CV, and IELTS 6.5 are required.",
    )
    chunk = Chunk(
        chunk_id=f"{SOURCE_ID}::0000",
        parent_id=parent.parent_id,
        source_id=SOURCE_ID,
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        source_authority=SourceAuthority.primary,
        lang=Language.en,
        country_scope=["all"],
        heading_path=["Required Documents"],
        text="Transcript, CV, IELTS 6.5",
        token_estimate=4,
    )
    return RetrievalResult(
        query="requirements",
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        hits=[RetrievedChunk(chunk=chunk, score=0.8)],
        sufficient_context=sufficient,
        top_score=0.8,
        parents=[parent] if with_parents else [],
    )


def _cited(source_id: str = SOURCE_ID) -> Citation:
    return Citation(source_id=source_id, heading_path=["Required Documents"])


# --- checklist -------------------------------------------------------------

def test_checklist_refuses_when_insufficient() -> None:
    result = generate_checklist(_result(sufficient=False), llm_client=_BoomLLM())
    assert result.insufficient_context is True
    assert result.items == []


def test_checklist_refuses_when_no_parents() -> None:
    result = generate_checklist(
        _result(sufficient=True, with_parents=False), llm_client=_BoomLLM()
    )
    assert result.insufficient_context is True


def test_checklist_returns_items_and_drops_bad_citations() -> None:
    canned = Checklist(
        items=[ChecklistItem(requirement="IELTS", detail="6.5 overall")],
        citations=[_cited(), _cited("hallucinated-src")],
        insufficient_context=False,
    )
    result = generate_checklist(_result(sufficient=True), llm_client=MockLLMClient(canned))
    assert [i.requirement for i in result.items] == ["IELTS"]
    assert [c.source_id for c in result.citations] == [SOURCE_ID]


def test_checklist_normalizes_model_insufficient_to_refusal() -> None:
    canned = Checklist(
        items=[ChecklistItem(requirement="x", detail="y")],
        citations=[],
        insufficient_context=True,
    )
    result = generate_checklist(_result(sufficient=True), llm_client=MockLLMClient(canned))
    assert result.insufficient_context is True
    assert result.items == []


# --- detect-missing --------------------------------------------------------

def test_detect_missing_refuses_when_insufficient() -> None:
    result = detect_missing_documents(["CV"], _result(sufficient=False), llm_client=_BoomLLM())
    assert result.insufficient_context is True
    assert result.missing == [] and result.satisfied == []


def test_detect_missing_returns_split_and_drops_bad_citations() -> None:
    canned = MissingDocsResult(
        missing=["IELTS 6.5"],
        satisfied=["Transcript", "CV"],
        citations=[_cited(), _cited("hallucinated-src")],
        insufficient_context=False,
    )
    result = detect_missing_documents(
        ["Transcript", "CV"], _result(sufficient=True), llm_client=MockLLMClient(canned)
    )
    assert result.missing == ["IELTS 6.5"]
    assert result.satisfied == ["Transcript", "CV"]
    assert [c.source_id for c in result.citations] == [SOURCE_ID]


# --- email -----------------------------------------------------------------

def test_email_refuses_when_insufficient() -> None:
    result = draft_email("ask about deadline", _result(sufficient=False), llm_client=_BoomLLM())
    assert result.insufficient_context is True
    assert result.subject == "" and result.body == ""


def test_email_returns_draft_and_drops_bad_citations() -> None:
    canned = EmailDraft(
        subject="Question about required documents",
        body="Dear Admissions Office, ...",
        citations=[_cited(), _cited("hallucinated-src")],
        insufficient_context=False,
    )
    result = draft_email("required documents", _result(sufficient=True), llm_client=MockLLMClient(canned))
    assert result.subject == "Question about required documents"
    assert result.body.startswith("Dear Admissions Office")
    assert [c.source_id for c in result.citations] == [SOURCE_ID]
