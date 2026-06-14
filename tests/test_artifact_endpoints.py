"""Tests for the artifact endpoints (offline; MockLLM + dependency overrides)."""

from fastapi.testclient import TestClient

from app.api.routes import provide_llm_client, provide_retriever
from app.main import app
from app.rag.artifacts import Checklist, ChecklistItem, EmailDraft, MissingDocsResult
from app.rag.generation import Citation, MockLLMClient
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
        parents=[parent],
    )


def _override(*, sufficient: bool, llm_client) -> None:  # type: ignore[no-untyped-def]
    def _provide_retriever():  # type: ignore[no-untyped-def]
        def _retrieve(query, *, university_slug, programme_slug=None):  # type: ignore[no-untyped-def]
            return _result(sufficient=sufficient)

        return _retrieve

    app.dependency_overrides[provide_retriever] = _provide_retriever
    app.dependency_overrides[provide_llm_client] = lambda: llm_client


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _citation() -> Citation:
    return Citation(source_id=SOURCE_ID, heading_path=["Required Documents"])


def test_checklist_returns_items() -> None:
    canned = Checklist(
        items=[ChecklistItem(requirement="IELTS", detail="6.5 overall")],
        citations=[_citation()],
        insufficient_context=False,
    )
    _override(sufficient=True, llm_client=MockLLMClient(canned))

    response = client.post(
        "/checklist",
        json={"university_slug": "uni-alpha", "programme_slug": "msc-data-science"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["requirement"] == "IELTS"
    assert body["insufficient_context"] is False
    assert body["disclaimer"]


def test_checklist_refuses_when_insufficient() -> None:
    _override(sufficient=False, llm_client=_BoomLLM())

    response = client.post(
        "/checklist",
        json={"university_slug": "uni-alpha", "programme_slug": "msc-data-science"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_context"] is True
    assert body["items"] == []


def test_checklist_requires_programme_slug() -> None:
    response = client.post("/checklist", json={"university_slug": "uni-alpha"})
    assert response.status_code == 422


def test_detect_missing_returns_split() -> None:
    canned = MissingDocsResult(
        missing=["IELTS 6.5"],
        satisfied=["Transcript"],
        citations=[_citation()],
        insufficient_context=False,
    )
    _override(sufficient=True, llm_client=MockLLMClient(canned))

    response = client.post(
        "/detect-missing",
        json={
            "university_slug": "uni-alpha",
            "programme_slug": "msc-data-science",
            "profile": ["Transcript"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["missing"] == ["IELTS 6.5"]
    assert body["satisfied"] == ["Transcript"]


def test_detect_missing_requires_programme_slug() -> None:
    response = client.post("/detect-missing", json={"university_slug": "uni-alpha"})
    assert response.status_code == 422


def test_draft_email_returns_draft() -> None:
    canned = EmailDraft(
        subject="Question about required documents",
        body="Dear Admissions Office, ...",
        citations=[_citation()],
        insufficient_context=False,
    )
    _override(sufficient=True, llm_client=MockLLMClient(canned))

    response = client.post(
        "/draft-email",
        json={"university_slug": "uni-alpha", "topic": "What documents are required?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "Question about required documents"
    assert body["body"].startswith("Dear Admissions Office")


def test_draft_email_refuses_when_insufficient() -> None:
    _override(sufficient=False, llm_client=_BoomLLM())

    response = client.post(
        "/draft-email", json={"university_slug": "uni-alpha", "topic": "anything"}
    )

    assert response.status_code == 200
    assert response.json()["insufficient_context"] is True


def test_draft_email_requires_topic() -> None:
    response = client.post("/draft-email", json={"university_slug": "uni-alpha"})
    assert response.status_code == 422
