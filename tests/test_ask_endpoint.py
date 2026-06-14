"""Tests for the /ask endpoint (offline; MockLLM + dependency overrides)."""

from fastapi.testclient import TestClient

from app.api.routes import provide_llm_client, provide_retriever
from app.main import app
from app.rag.generation import (
    Citation,
    GroundedAnswer,
    MockLLMClient,
    REFUSAL_MESSAGE,
)
from app.rag.metadata import Chunk, Language, ParentSection, SourceAuthority
from app.rag.retrieval import RetrievalResult, RetrievedChunk

client = TestClient(app)
SOURCE_ID = "alpha-src"


class _BoomLLM:
    def generate(self, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("LLM must not be called when context is insufficient")


def _result(*, sufficient: bool) -> RetrievalResult:
    parent = ParentSection(
        parent_id=f"{SOURCE_ID}::section::000",
        source_id=SOURCE_ID,
        heading_path=["Language Requirements"],
        text="IELTS 6.5 overall is required.",
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
        heading_path=["Language Requirements"],
        text="IELTS 6.5",
        token_estimate=2,
    )
    return RetrievalResult(
        query="q",
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        hits=[RetrievedChunk(chunk=chunk, score=0.8)],
        sufficient_context=sufficient,
        top_score=0.8,
        parents=[parent],
    )


def _override(*, sufficient: bool, llm_client) -> None:  # type: ignore[no-untyped-def]
    def _provide_retriever():  # type: ignore[no-untyped-def]
        def _retrieve(question, *, university_slug, programme_slug=None):  # type: ignore[no-untyped-def]
            return _result(sufficient=sufficient)

        return _retrieve

    app.dependency_overrides[provide_retriever] = _provide_retriever
    app.dependency_overrides[provide_llm_client] = lambda: llm_client


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_ask_returns_grounded_answer() -> None:
    canned = GroundedAnswer(
        answer="IELTS 6.5 overall is required.",
        citations=[Citation(source_id=SOURCE_ID, heading_path=["Language Requirements"])],
        insufficient_context=False,
        confidence=0.9,
    )
    _override(sufficient=True, llm_client=MockLLMClient(canned))

    response = client.post(
        "/ask",
        json={
            "question": "What IELTS score is required?",
            "university_slug": "uni-alpha",
            "programme_slug": "msc-data-science",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "IELTS 6.5 overall is required."
    assert body["citations"][0]["source_id"] == SOURCE_ID
    assert body["insufficient_context"] is False
    assert body["university_slug"] == "uni-alpha"
    assert body["disclaimer"]


def test_ask_refuses_when_insufficient_context() -> None:
    _override(sufficient=False, llm_client=_BoomLLM())

    response = client.post(
        "/ask", json={"question": "anything", "university_slug": "uni-alpha"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == REFUSAL_MESSAGE
    assert body["insufficient_context"] is True
    assert body["citations"] == []


def test_ask_requires_university_slug() -> None:
    response = client.post("/ask", json={"question": "anything"})

    assert response.status_code == 422


def test_ask_rejects_empty_question() -> None:
    response = client.post("/ask", json={"question": "", "university_slug": "uni-alpha"})

    assert response.status_code == 422
