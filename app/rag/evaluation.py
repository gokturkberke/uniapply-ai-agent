"""Lightweight, in-repo evaluation harness for the RAG pipeline.

Replays a gold question set through ``retrieve_with_parents`` + ``generate_grounded_answer``
and scores deterministic metrics (retrieval recall@k vs expected source ids, refusal /
out-of-scope correctness) plus an LLM-judge faithfulness rate (reusing the ``LLMClient``
abstraction). No third-party eval framework; fully offline-testable with MockLLM and an
injected ``retrieve_fn``. Deterministic given a fixed gold set and pinned models (no sampling).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.rag.generation import (
    LLMClient,
    format_context,
    generate_grounded_answer,
    safe_generate,
)
from app.rag.retrieval import RetrievalResult, retrieve_with_parents

# RAG-Triad-style reference targets (notes 03 §6 / 04 §9).
TARGETS = {
    "faithfulness_rate": 0.95,
    "retrieval_recall": 0.90,
    "refusal_accuracy": 1.0,
    "citation_grounding_rate": 1.0,
}


class GoldQuestion(BaseModel):
    """One labeled evaluation question."""

    id: str
    question: str
    university_slug: str
    programme_slug: str | None = None
    category: Literal["factual", "multi_hop", "reformulation", "out_of_scope"]
    expected_source_ids: list[str] = Field(default_factory=list)
    should_refuse: bool = False


class FaithfulnessVerdict(BaseModel):
    """LLM-judge verdict: is the answer fully supported by the context?"""

    supported: bool
    reasoning: str


class QuestionResult(BaseModel):
    """Per-question evaluation outcome.

    Float metrics are ``None`` when not applicable: retrieval/citation recall need
    expected source ids; citation grounding and faithfulness need an answered (not
    refused) question.
    """

    id: str
    category: str
    refused: bool
    refusal_correct: bool
    expected_source_ids: list[str]
    retrieved_source_ids: list[str]
    cited_source_ids: list[str]
    retrieval_recall: float | None
    citation_recall: float | None
    citation_grounding: bool | None
    faithful: bool | None


class EvalReport(BaseModel):
    """Aggregated evaluation report."""

    total: int
    retrieval_recall: float
    citation_recall: float
    citation_grounding_rate: float
    refusal_accuracy: float
    faithfulness_rate: float
    by_category: dict[str, int]
    results: list[QuestionResult]


def load_gold_set(path: Path | None = None) -> list[GoldQuestion]:
    """Load a JSONL gold set into validated questions (empty if the file is absent)."""

    gold_path = path or Path(get_settings().eval_gold_path)
    if not gold_path.is_file():
        return []

    questions: list[GoldQuestion] = []
    for line_number, line in enumerate(
        gold_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            questions.append(GoldQuestion.model_validate_json(line))
        except ValidationError as exc:
            raise ValueError(
                f"invalid gold question on line {line_number} of {gold_path}: {exc}"
            ) from exc
    return questions


def judge_faithfulness(
    question: str,
    answer: str,
    retrieval_result: RetrievalResult,
    *,
    judge_client: LLMClient,
) -> FaithfulnessVerdict:
    """Judge whether every claim in the answer is supported by the retrieved context."""

    system = (
        "You are a strict RAG faithfulness evaluator. Decide whether EVERY claim in the "
        "ANSWER is directly supported by the CONTEXT. Set supported=false if any claim is "
        "unsupported, contradicts the context, or is not derivable from it."
    )
    user = (
        f"Question:\n{question}\n\nAnswer:\n{answer}\n\n"
        f"Context:\n{format_context(retrieval_result)}"
    )
    return safe_generate(
        judge_client,
        system=system,
        user=user,
        output_model=FaithfulnessVerdict,
        fallback=FaithfulnessVerdict(
            supported=False, reasoning="conservative fallback: unparseable judge output"
        ),
    )


def _rate(flags: list[bool]) -> float:
    return sum(flags) / len(flags) if flags else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _recall(expected: set[str], actual: set[str]) -> float:
    """Fraction of expected source ids present in ``actual`` (expected must be non-empty)."""

    return len(expected & actual) / len(expected)


def _citation_grounding(cited: set[str], retrieved: set[str]) -> bool:
    """True when every cited source id is present in the retrieved context."""

    return cited.issubset(retrieved)


def _aggregate(results: list[QuestionResult]) -> EvalReport:
    by_category: dict[str, int] = {}
    for result in results:
        by_category[result.category] = by_category.get(result.category, 0) + 1

    return EvalReport(
        total=len(results),
        retrieval_recall=_mean([r.retrieval_recall for r in results if r.retrieval_recall is not None]),
        citation_recall=_mean([r.citation_recall for r in results if r.citation_recall is not None]),
        citation_grounding_rate=_rate(
            [r.citation_grounding for r in results if r.citation_grounding is not None]
        ),
        refusal_accuracy=_rate([r.refusal_correct for r in results]),
        faithfulness_rate=_rate([r.faithful for r in results if r.faithful is not None]),
        by_category=by_category,
        results=results,
    )


def evaluate_gold_set(
    gold: list[GoldQuestion],
    *,
    answer_client: LLMClient,
    judge_client: LLMClient,
    retrieve_fn: Callable[..., RetrievalResult] = retrieve_with_parents,
) -> EvalReport:
    """Run each gold question through retrieval + grounded generation and score it."""

    results: list[QuestionResult] = []
    for question in gold:
        retrieval_result = retrieve_fn(
            question.question,
            university_slug=question.university_slug,
            programme_slug=question.programme_slug,
        )
        answer = generate_grounded_answer(
            question.question, retrieval_result, llm_client=answer_client
        )
        refused = answer.insufficient_context

        expected = set(question.expected_source_ids)
        retrieved = {hit.chunk.source_id for hit in retrieval_result.hits}
        cited = {citation.source_id for citation in answer.citations}

        retrieval_recall = _recall(expected, retrieved) if expected else None

        citation_recall: float | None = None
        citation_grounding: bool | None = None
        faithful: bool | None = None
        if not refused:
            citation_grounding = _citation_grounding(cited, retrieved)
            if expected:
                citation_recall = _recall(expected, cited)
            verdict = judge_faithfulness(
                question.question, answer.answer, retrieval_result, judge_client=judge_client
            )
            faithful = verdict.supported

        results.append(
            QuestionResult(
                id=question.id,
                category=question.category,
                refused=refused,
                refusal_correct=refused == question.should_refuse,
                expected_source_ids=question.expected_source_ids,
                retrieved_source_ids=sorted(retrieved),
                cited_source_ids=sorted(cited),
                retrieval_recall=retrieval_recall,
                citation_recall=citation_recall,
                citation_grounding=citation_grounding,
                faithful=faithful,
            )
        )

    return _aggregate(results)
