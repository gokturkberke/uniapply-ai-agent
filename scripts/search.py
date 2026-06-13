"""Manual retrieval entrypoint (debug / verification).

Run from the repository root against an existing on-disk index:

    python -m scripts.search "application deadline" --university tum-munich --programme msc-data-science

Prints each scope-filtered hit and the Retrieval Gate decision. Uses the
configured embedding provider (downloads the fastembed model on first real use).
"""

import argparse

from app.rag.retrieval import retrieve_with_parents


def main() -> None:
    parser = argparse.ArgumentParser(description="Scope-filtered dense retrieval over the index.")
    parser.add_argument("query", help="The user question to retrieve context for.")
    parser.add_argument("--university", required=True, help="university_slug to scope to.")
    parser.add_argument("--programme", default=None, help="Optional programme_slug to scope to.")
    args = parser.parse_args()

    result = retrieve_with_parents(
        args.query,
        university_slug=args.university,
        programme_slug=args.programme,
    )

    print(
        f"sufficient_context={result.sufficient_context} "
        f"top_score={result.top_score} hits={len(result.hits)} parents={len(result.parents)}"
    )
    print("-- matched chunks --")
    for hit in result.hits:
        heading = " > ".join(hit.chunk.heading_path) or "(no heading)"
        snippet = hit.chunk.text[:160].replace("\n", " ")
        print(f"[{hit.score:.3f}] {hit.chunk.source_id} | {heading}\n    {snippet}")
    print("-- parent sections (grounding context) --")
    for parent in result.parents:
        heading = " > ".join(parent.heading_path) or "(no heading)"
        snippet = parent.text[:200].replace("\n", " ")
        print(f"{parent.source_id} | {heading}\n    {snippet}")


if __name__ == "__main__":
    main()
