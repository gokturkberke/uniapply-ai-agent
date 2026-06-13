"""Offline ingestion entrypoint.

Run from the repository root:

    python -m scripts.ingest

Normalizes every source in the registry from the raw archive into the
normalized layer and prints a one-line summary per source.
"""

from app.rag.ingestion import normalize_registry


def main() -> None:
    results = normalize_registry()
    if not results:
        print("Nothing to normalize: registry is empty.")
        return
    for result in results:
        print(
            f"{result.source_id}\t{result.status}\t"
            f"{result.char_count} chars\t{result.normalized_path or '-'}"
        )


if __name__ == "__main__":
    main()
