"""Tests for the indexing pipeline using a fake embedder + in-memory Qdrant (offline)."""

from pathlib import Path

from qdrant_client import QdrantClient

from app.rag.embeddings import FakeEmbedder
from app.rag.indexing import index_corpus, load_chunk_artifacts
from app.rag.metadata import (
    Chunk,
    ChunkingResult,
    Language,
    ParentSection,
    SourceAuthority,
)
from app.rag.vector_store import VectorStore


def _result(university_slug: str, chunk_count: int) -> ChunkingResult:
    source_id = f"{university_slug}-src"
    parent = ParentSection(
        parent_id=f"{source_id}::section::000",
        source_id=source_id,
        heading_path=["Heading"],
        text="parent section text",
    )
    chunks = [
        Chunk(
            chunk_id=f"{source_id}::{index:04d}",
            parent_id=parent.parent_id,
            source_id=source_id,
            university_slug=university_slug,
            programme_slug="msc-data-science",
            source_authority=SourceAuthority.primary,
            lang=Language.en,
            country_scope=["all"],
            heading_path=["Heading"],
            text=f"{university_slug} chunk number {index}",
            token_estimate=4,
        )
        for index in range(chunk_count)
    ]
    return ChunkingResult(source_id=source_id, parents=[parent], chunks=chunks)


def _write_artifacts(chunk_dir: Path) -> int:
    chunk_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for university_slug, chunk_count in [("uni-alpha", 3), ("uni-beta", 2)]:
        result = _result(university_slug, chunk_count)
        (chunk_dir / f"{result.source_id}.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        total += chunk_count
    # A manifest.json that must be ignored by the loader.
    (chunk_dir / "manifest.json").write_text("[]", encoding="utf-8")
    return total


def test_index_corpus_indexes_all_chunks(tmp_path: Path) -> None:
    chunk_dir = tmp_path / "chunks"
    total = _write_artifacts(chunk_dir)
    embedder = FakeEmbedder()
    store = VectorStore(QdrantClient(location=":memory:"), "idx_test")

    result = index_corpus(
        chunk_dir=chunk_dir, vector_store=store, embedder=embedder, batch_size=2
    )

    assert result.indexed_count == total
    assert result.source_count == 2
    assert store.count() == total

    hits = store.search(embedder.embed_query("q"), university_slug="uni-alpha", limit=10)
    assert hits
    assert all(hit.payload["university_slug"] == "uni-alpha" for hit in hits)


def test_load_chunk_artifacts_skips_manifest(tmp_path: Path) -> None:
    chunk_dir = tmp_path / "chunks"
    _write_artifacts(chunk_dir)

    source_ids = {source_id for source_id, _ in load_chunk_artifacts(chunk_dir)}

    assert source_ids == {"uni-alpha-src", "uni-beta-src"}


def test_index_corpus_empty_dir(tmp_path: Path) -> None:
    store = VectorStore(QdrantClient(location=":memory:"), "empty_test")

    result = index_corpus(
        chunk_dir=tmp_path / "missing", vector_store=store, embedder=FakeEmbedder()
    )

    assert result.indexed_count == 0
    assert result.source_count == 0
