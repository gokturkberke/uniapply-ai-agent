"""Offline evaluation entrypoint.

Run from the repository root (needs a configured LLM provider - e.g.
LLM_PROVIDER=local_openai with a running Ollama - a built index, and a curated
gold set at EVAL_GOLD_PATH for real numbers):

    python -m scripts.evaluate --run-label baseline

Replays the gold set through retrieval + grounded generation, scores retrieval recall,
refusal correctness, and LLM-judged faithfulness, writes the report under the runs dir,
and prints a summary against the reference targets.
"""

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.rag.evaluation import TARGETS, evaluate_gold_set, load_gold_set
from app.rag.generation import get_llm_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the gold set against the RAG pipeline.")
    parser.add_argument(
        "--run-label", default="latest", help="Subdirectory name under the runs dir."
    )
    args = parser.parse_args()

    settings = get_settings()
    gold = load_gold_set()
    if not gold:
        print(f"Nothing to evaluate: gold set is empty or missing ({settings.eval_gold_path}).")
        return

    llm_client = get_llm_client(settings)
    report = evaluate_gold_set(gold, answer_client=llm_client, judge_client=llm_client)

    run_dir = Path(settings.eval_runs_dir) / args.run_label
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print(f"Evaluated {report.total} questions -> {report_path}")
    print(f"retrieval_recall        = {report.retrieval_recall:.3f} (target {TARGETS['retrieval_recall']})")
    print(f"citation_recall         = {report.citation_recall:.3f}")
    print(f"citation_grounding_rate = {report.citation_grounding_rate:.3f} (target {TARGETS['citation_grounding_rate']})")
    print(f"refusal_accuracy        = {report.refusal_accuracy:.3f} (target {TARGETS['refusal_accuracy']})")
    print(f"faithfulness_rate       = {report.faithfulness_rate:.3f} (target {TARGETS['faithfulness_rate']})")
    print(f"by_category             = {report.by_category}")


if __name__ == "__main__":
    main()
