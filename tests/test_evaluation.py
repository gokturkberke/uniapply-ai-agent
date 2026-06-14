"""Tests for the evaluation harness (offline, MockLLM + stubbed retrieval)."""

from pathlib import Path

import pytest

from app.rag.evaluation import (
    FaithfulnessVerdict,
    GoldQuestion,
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
    assert report.faithfulness_rate == 1.0  # over the one answered question
    assert report.by_category == {"factual": 1, "out_of_scope": 1}

    by_id = {r.id: r for r in report.results}
    assert by_id["q-factual-1"].refused is False
    assert by_id["q-factual-1"].retrieval_hit is True
    assert by_id["q-factual-1"].faithful is True
    assert by_id["q-oos-1"].refused is True
    assert by_id["q-oos-1"].refusal_correct is True
    assert by_id["q-oos-1"].retrieval_hit is None
    assert by_id["q-oos-1"].faithful is None
