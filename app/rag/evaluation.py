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
from app.rag.generation import LLMClient, format_context, generate_grounded_answer
from app.rag.retrieval import RetrievalResult, retrieve_with_parents

# RAG-Triad-style reference targets (notes 03 §6 / 04 §9).
TARGETS = {"faithfulness_rate": 0.95, "retrieval_recall": 0.90, "refusal_accuracy": 1.0}


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
    """Per-question evaluation outcome."""

    id: str
    category: str
    refused: bool
    refusal_correct: bool
    retrieval_hit: bool | None
    faithful: bool | None


class EvalReport(BaseModel):
    """Aggregated evaluation report."""

    total: int
    retrieval_recall: float
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
    return judge_client.generate(
        system=system, user=user, output_model=FaithfulnessVerdict
    )


def _rate(flags: list[bool]) -> float:
    return sum(flags) / len(flags) if flags else 0.0


def _aggregate(results: list[QuestionResult]) -> EvalReport:
    by_category: dict[str, int] = {}
    for result in results:
        by_category[result.category] = by_category.get(result.category, 0) + 1

    return EvalReport(
        total=len(results),
        retrieval_recall=_rate([r.retrieval_hit for r in results if r.retrieval_hit is not None]),
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

        retrieval_hit: bool | None = None
        if question.expected_source_ids:
            retrieved = {hit.chunk.source_id for hit in retrieval_result.hits}
            retrieval_hit = bool(set(question.expected_source_ids) & retrieved)

        faithful: bool | None = None
        if not refused:
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
                retrieval_hit=retrieval_hit,
                faithful=faithful,
            )
        )

    return _aggregate(results)
