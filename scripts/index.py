"""Offline indexing entrypoint.

Run from the repository root:

    python -m scripts.index

Embeds every chunk artifact in the chunk layer and upserts them into the local
Qdrant collection, using the configured embedding provider (downloads the
fastembed model on first real use).
"""

from app.rag.indexing import index_corpus


def main() -> None:
    result = index_corpus()
    if result.indexed_count == 0:
        print("Nothing to index: no chunk artifacts found.")
        return
    print(
        f"Indexed {result.indexed_count} chunks from {result.source_count} sources "
        f"into '{result.collection}' (model={result.model_id}, dim={result.dimension})."
    )


if __name__ == "__main__":
    main()
