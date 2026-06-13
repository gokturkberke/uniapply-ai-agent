"""Tests for the Qdrant vector store using in-memory local mode (offline)."""

import pytest
from qdrant_client import QdrantClient

from app.rag.embeddings import FakeEmbedder
from app.rag.metadata import Chunk, Language, SourceAuthority
from app.rag.vector_store import VectorStore


def _chunk(chunk_id: str, university_slug: str, text: str = "some chunk text") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        parent_id=f"{university_slug}-src::section::000",
        source_id=f"{university_slug}-src",
        university_slug=university_slug,
        programme_slug="msc-data-science",
        source_authority=SourceAuthority.primary,
        lang=Language.en,
        country_scope=["all"],
        heading_path=["Heading"],
        text=text,
        token_estimate=len(text.split()),
    )


def _store() -> VectorStore:
    return VectorStore(QdrantClient(location=":memory:"), "test_chunks")


def test_upsert_and_count() -> None:
    store = _store()
    embedder = FakeEmbedder()
    store.ensure_collection(embedder.dimension, reset=True)
    chunks = [_chunk("uni-alpha::0000", "uni-alpha"), _chunk("uni-beta::0000", "uni-beta")]

    indexed = store.upsert_chunks(chunks, embedder.embed_texts([c.text for c in chunks]))

    assert indexed == 2
    assert store.count() == 2


def test_search_filters_by_university() -> None:
    store = _store()
    embedder = FakeEmbedder()
    store.ensure_collection(embedder.dimension, reset=True)
    chunks = [
        _chunk("uni-alpha::0000", "uni-alpha"),
        _chunk("uni-alpha::0001", "uni-alpha"),
        _chunk("uni-beta::0000", "uni-beta"),
    ]
    store.upsert_chunks(chunks, embedder.embed_texts([c.text for c in chunks]))

    hits = store.search(embedder.embed_query("query"), university_slug="uni-alpha", limit=10)

    assert hits
    assert all(hit.payload["university_slug"] == "uni-alpha" for hit in hits)
    assert all("text" in hit.payload and "source_id" in hit.payload for hit in hits)


def test_upsert_length_mismatch_raises() -> None:
    store = _store()
    store.ensure_collection(8, reset=True)

    with pytest.raises(ValueError, match="same length"):
        store.upsert_chunks([_chunk("uni-x::0000", "uni-x")], [])
