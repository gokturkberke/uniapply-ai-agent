"""Offline indexing: embed chunk artifacts and upsert them into the vector store.

Reads the per-source chunk artifacts produced by the chunking phase, embeds each
chunk, and writes vectors + metadata payloads into Qdrant. One source file is read
at a time and embedded in batches (memory-safe). No network beyond the embedder's
own model load.
"""

from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

from app.core.config import get_settings
from app.rag.embeddings import Embedder, get_embedder
from app.rag.metadata import Chunk, ChunkingResult
from app.rag.vector_store import VectorStore


class IndexResult(BaseModel):
    """Summary of an index build."""

    collection: str
    model_id: str
    dimension: int
    source_count: int
    indexed_count: int


def load_chunk_artifacts(chunk_dir: Path) -> Iterator[tuple[str, list[Chunk]]]:
    """Yield ``(source_id, chunks)`` for each chunk artifact, one file at a time."""

    if not chunk_dir.is_dir():
        return
    for path in sorted(chunk_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        result = ChunkingResult.model_validate_json(path.read_text(encoding="utf-8"))
        yield result.source_id, result.chunks


def _batched(chunks: list[Chunk], size: int) -> Iterator[list[Chunk]]:
    for start in range(0, len(chunks), size):
        yield chunks[start : start + size]


def index_corpus(
    *,
    chunk_dir: Path | None = None,
    vector_store: VectorStore | None = None,
    embedder: Embedder | None = None,
    batch_size: int | None = None,
    reset: bool = True,
) -> IndexResult:
    """Embed every chunk artifact and upsert it into the vector store."""

    settings = get_settings()
    if chunk_dir is None:
        chunk_dir = Path(settings.chunk_dir)
    if embedder is None:
        embedder = get_embedder(settings)
    if vector_store is None:
        vector_store = VectorStore.from_settings()
    if batch_size is None:
        batch_size = settings.embedding_batch_size

    dimension = embedder.dimension
    vector_store.ensure_collection(dimension, reset=reset)

    source_count = 0
    indexed_count = 0
    for _source_id, chunks in load_chunk_artifacts(chunk_dir):
        source_count += 1
        for batch in _batched(chunks, batch_size):
            vectors = embedder.embed_texts([chunk.text for chunk in batch])
            indexed_count += vector_store.upsert_chunks(batch, vectors)

    return IndexResult(
        collection=vector_store.collection,
        model_id=embedder.model_id,
        dimension=dimension,
        source_count=source_count,
        indexed_count=indexed_count,
    )
