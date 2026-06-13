"""Offline chunking entrypoint.

Run from the repository root:

    python -m scripts.chunk

Chunks every normalized source in the registry into the chunk layer and prints
a one-line summary per source.
"""

from app.rag.chunking import chunk_corpus


def main() -> None:
    summaries = chunk_corpus()
    if not summaries:
        print("Nothing to chunk: registry is empty.")
        return
    for summary in summaries:
        print(
            f"{summary.source_id}\t{summary.status}\t"
            f"{summary.chunk_count} chunks\t{summary.parent_count} parents\t"
            f"{summary.chunk_path or '-'}"
        )


if __name__ == "__main__":
    main()
