"""Tests for the evaluation harness (offline, MockLLM + stubbed retrieval)."""

from pathlib import Path

import pytest

from app.rag.evaluation import (
    FaithfulnessVerdict,
    GoldQuestion,
    _citation_grounding,
    _recall,
    evaluate_gold_set,
    judge_faithfulness,
    load_gold_set,
)
from app.rag.generation import Citation, GroundedAnswer, MockLLMClient
from app.rag.metadata import Chunk, Language, ParentSection, SourceAuthority
from app.rag.retrieval import RetrievalResult, RetrievedChunk

FIXTURE = Path(__file__).parent / "fixtures" / "eval" / "gold_sample.jsonl"
SOURCE_ID = "alpha-src"


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
        top_score=0.8 if sufficient else 0.1,
        parents=[parent] if sufficient else [],
    )


def test_load_gold_set_parses_fixture() -> None:
    gold = load_gold_set(FIXTURE)

    assert {q.id for q in gold} == {"q-factual-1", "q-oos-1"}
    assert {q.category for q in gold} == {"factual", "out_of_scope"}
    oos = next(q for q in gold if q.category == "out_of_scope")
    assert oos.should_refuse is True


def test_load_gold_set_rejects_malformed_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id": "x"}\n', encoding="utf-8")  # missing required fields

    with pytest.raises(ValueError, match="invalid gold question on line 1"):
        load_gold_set(path)


def test_load_gold_set_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_gold_set(tmp_path / "absent.jsonl") == []


def test_judge_faithfulness_returns_verdict() -> None:
    judge = MockLLMClient(FaithfulnessVerdict(supported=True, reasoning="all claims supported"))

    verdict = judge_faithfulness("q", "answer", _result(sufficient=True), judge_client=judge)

    assert verdict.supported is True


def test_evaluate_gold_set_aggregates_metrics() -> None:
    gold = [
        GoldQuestion(
            id="q-factual-1",
            question="What IELTS score is required?",
            university_slug="uni-alpha",
            programme_slug="msc-data-science",
            category="factual",
            expected_source_ids=[SOURCE_ID],
            should_refuse=False,
        ),
        GoldQuestion(
            id="q-oos-1",
            question="What are the study visa rules for Canada?",
            university_slug="uni-alpha",
            programme_slug="msc-data-science",
            category="out_of_scope",
            expected_source_ids=[],
            should_refuse=True,
        ),
    ]

    def _retrieve(question, *, university_slug, programme_slug=None):  # type: ignore[no-untyped-def]
        # Factual question has grounding context; the out-of-scope one does not.
        return _result(sufficient="IELTS" in question)

    answer_client = MockLLMClient(
        GroundedAnswer(
            answer="IELTS 6.5 overall is required.",
            citations=[Citation(source_id=SOURCE_ID, heading_path=["Language Requirements"])],
            insufficient_context=False,
            confidence=0.9,
        )
    )
    judge_client = MockLLMClient(FaithfulnessVerdict(supported=True, reasoning="ok"))

    report = evaluate_gold_set(
        gold, answer_client=answer_client, judge_client=judge_client, retrieve_fn=_retrieve
    )

    assert report.total == 2
    assert report.refusal_accuracy == 1.0
    assert report.retrieval_recall == 1.0  # over the one question with expected sources
    assert report.citation_recall == 1.0
    assert report.citation_grounding_rate == 1.0
    assert report.faithfulness_rate == 1.0  # over the one answered question
    assert report.by_category == {"factual": 1, "out_of_scope": 1}

    by_id = {r.id: r for r in report.results}
    assert by_id["q-factual-1"].refused is False
    assert by_id["q-factual-1"].retrieval_recall == 1.0
    assert by_id["q-factual-1"].citation_recall == 1.0
    assert by_id["q-factual-1"].citation_grounding is True
    assert by_id["q-factual-1"].faithful is True
    assert by_id["q-oos-1"].refused is True
    assert by_id["q-oos-1"].refusal_correct is True
    assert by_id["q-oos-1"].retrieval_recall is None
    assert by_id["q-oos-1"].citation_recall is None
    assert by_id["q-oos-1"].citation_grounding is None
    assert by_id["q-oos-1"].faithful is None


def _result_for(source_id: str) -> RetrievalResult:
    parent = ParentSection(
        parent_id=f"{source_id}::section::000",
        source_id=source_id,
        heading_path=["H"],
        text="context",
    )
    chunk = Chunk(
        chunk_id=f"{source_id}::0000",
        parent_id=parent.parent_id,
        source_id=source_id,
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        source_authority=SourceAuthority.primary,
        lang=Language.en,
        country_scope=["all"],
        heading_path=["H"],
        text="x",
        token_estimate=1,
    )
    return RetrievalResult(
        query="q",
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        hits=[RetrievedChunk(chunk=chunk, score=0.8)],
        sufficient_context=True,
        top_score=0.8,
        parents=[parent],
    )


def test_partial_recall_when_one_of_two_expected_sources() -> None:
    # Multi-hop question expects s1 + s2, but only s1 is retrieved and cited.
    gold = [
        GoldQuestion(
            id="q-multi-1",
            question="multi-hop question",
            university_slug="uni-alpha",
            programme_slug="msc-data-science",
            category="multi_hop",
            expected_source_ids=["s1", "s2"],
            should_refuse=False,
        )
    ]
    answer_client = MockLLMClient(
        GroundedAnswer(
            answer="partial answer",
            citations=[Citation(source_id="s1", heading_path=["H"])],
            insufficient_context=False,
            confidence=0.8,
        )
    )
    judge_client = MockLLMClient(FaithfulnessVerdict(supported=True, reasoning="ok"))

    report = evaluate_gold_set(
        gold,
        answer_client=answer_client,
        judge_client=judge_client,
        retrieve_fn=lambda question, **_kwargs: _result_for("s1"),
    )

    result = report.results[0]
    assert result.retrieval_recall == 0.5  # 1 of 2 expected retrieved
    assert result.citation_recall == 0.5  # 1 of 2 expected cited
    assert result.citation_grounding is True  # s1 is in the retrieved context
    assert report.retrieval_recall == 0.5


def test_citation_grounding_detects_out_of_context() -> None:
    assert _citation_grounding({"s1", "hallucinated"}, {"s1"}) is False
    assert _citation_grounding({"s1"}, {"s1", "s2"}) is True


def test_recall_fraction() -> None:
    assert _recall({"s1", "s2"}, {"s1"}) == 0.5
    assert _recall({"s1", "s2"}, {"s1", "s2"}) == 1.0
