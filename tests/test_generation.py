"""Tests for grounded answer generation (offline, MockLLM)."""

from app.rag.generation import (
    Citation,
    GroundedAnswer,
    MockLLMClient,
    REFUSAL_MESSAGE,
    build_grounded_prompt,
    generate_grounded_answer,
)
from app.rag.metadata import Chunk, Language, ParentSection, SourceAuthority
from app.rag.retrieval import RetrievalResult, RetrievedChunk

SOURCE_ID = "alpha-src"


class _BoomLLM:
    """LLM that fails if called — proves the refusal path skips the LLM."""

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


def test_refusal_when_insufficient_context() -> None:
    answer = generate_grounded_answer("q", _result(sufficient=False), llm_client=_BoomLLM())

    assert answer.answer == REFUSAL_MESSAGE
    assert answer.insufficient_context is True
    assert answer.citations == []
    assert answer.confidence == 0.0


def test_grounded_answer_when_sufficient() -> None:
    canned = GroundedAnswer(
        answer="IELTS 6.5 overall is required.",
        citations=[Citation(source_id=SOURCE_ID, heading_path=["Language Requirements"])],
        insufficient_context=False,
        confidence=0.9,
    )

    answer = generate_grounded_answer(
        "q", _result(sufficient=True), llm_client=MockLLMClient(canned)
    )

    assert answer.answer == "IELTS 6.5 overall is required."
    assert [c.source_id for c in answer.citations] == [SOURCE_ID]


def test_citations_outside_context_are_dropped() -> None:
    canned = GroundedAnswer(
        answer="...",
        citations=[
            Citation(source_id=SOURCE_ID, heading_path=["Language Requirements"]),
            Citation(source_id="hallucinated-src", heading_path=["Made Up"]),
        ],
        insufficient_context=False,
        confidence=0.5,
    )

    answer = generate_grounded_answer(
        "q", _result(sufficient=True), llm_client=MockLLMClient(canned)
    )

    assert [c.source_id for c in answer.citations] == [SOURCE_ID]  # hallucination dropped


def test_refuses_when_no_parents_even_if_gate_sufficient() -> None:
    # Parent/artifact drift: gate passes but there is no grounding context.
    result = _result(sufficient=True).model_copy(update={"parents": []})

    answer = generate_grounded_answer("q", result, llm_client=_BoomLLM())

    assert answer.answer == REFUSAL_MESSAGE  # refuse without calling the LLM
    assert answer.insufficient_context is True
    assert answer.citations == []


def test_model_insufficient_flag_is_normalized_to_refusal() -> None:
    # The model judged context insufficient but emitted non-refusal text.
    canned = GroundedAnswer(
        answer="Maybe IELTS 6.5.",
        citations=[Citation(source_id=SOURCE_ID, heading_path=["Language Requirements"])],
        insufficient_context=True,
        confidence=0.2,
    )

    answer = generate_grounded_answer(
        "q", _result(sufficient=True), llm_client=MockLLMClient(canned)
    )

    assert answer.answer == REFUSAL_MESSAGE
    assert answer.insufficient_context is True
    assert answer.citations == []


def test_prompt_includes_context_and_refusal_instruction() -> None:
    system, user = build_grounded_prompt("What IELTS score?", _result(sufficient=True))

    assert REFUSAL_MESSAGE in system
    assert "IELTS 6.5 overall is required." in user
    assert SOURCE_ID in user
