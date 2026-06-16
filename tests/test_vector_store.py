"""Tests for the Qdrant vector store using in-memory local mode (offline)."""

import pytest
from qdrant_client import QdrantClient

from app.rag.embeddings import FakeEmbedder
from app.rag.metadata import Chunk, Language, SourceAuthority
from app.rag.vector_store import VectorStore


def _chunk(
    chunk_id: str,
    university_slug: str,
    programme_slug: str = "msc-data-science",
    text: str = "some chunk text",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        parent_id=f"{university_slug}-{programme_slug}::section::000",
        source_id=f"{university_slug}-{programme_slug}",
        university_slug=university_slug,
        programme_slug=programme_slug,
        source_authority=SourceAuthority.primary,
        lang=Language.en,
        country_scope=["all"],
        heading_path=["Heading"],
        text=text,
        token_estimate=len(text.split()),
    )


def _store() -> VectorStore:
    return VectorStore(QdrantClient(location=":memory:"), "test_chunks")


def test_from_settings_uses_server_url_when_qdrant_url_set(monkeypatch) -> None:
    """When ``qdrant_url`` is set, the client is built in server mode (no live server needed)."""

    from app.core.config import Settings

    captured: dict = {}
    monkeypatch.setattr(
        "app.rag.vector_store.QdrantClient",
        lambda **kwargs: captured.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        "app.rag.vector_store.get_settings",
        lambda: Settings(qdrant_url="http://qdrant:6333"),
    )

    VectorStore.from_settings()

    assert captured == {"url": "http://qdrant:6333"}


def test_from_settings_embedded_when_qdrant_url_unset(monkeypatch, tmp_path) -> None:
    """Default (qdrant_url unset) stays embedded on-disk mode - behavior unchanged."""

    from app.core.config import Settings

    captured: dict = {}
    monkeypatch.setattr(
        "app.rag.vector_store.QdrantClient",
        lambda **kwargs: captured.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        "app.rag.vector_store.get_settings",
        lambda: Settings(qdrant_url=None, qdrant_path=str(tmp_path / "idx")),
    )

    VectorStore.from_settings()

    assert "url" not in captured
    assert captured.get("path") == str(tmp_path / "idx")


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


def test_search_isolates_by_programme_within_same_university() -> None:
    # The critical domain rule: scope is university AND programme, not just
    # university. Two programmes at the same university must never blend.
    store = _store()
    embedder = FakeEmbedder()
    store.ensure_collection(embedder.dimension, reset=True)
    chunks = [
        _chunk("uni-alpha-ds::0000", "uni-alpha", "msc-data-science"),
        _chunk("uni-alpha-ds::0001", "uni-alpha", "msc-data-science"),
        _chunk("uni-alpha-cs::0000", "uni-alpha", "msc-computer-science"),
    ]
    store.upsert_chunks(chunks, embedder.embed_texts([c.text for c in chunks]))
    query = embedder.embed_query("query")

    data_science = store.search(
        query, university_slug="uni-alpha", programme_slug="msc-data-science", limit=10
    )
    assert {hit.payload["chunk_id"] for hit in data_science} == {
        "uni-alpha-ds::0000",
        "uni-alpha-ds::0001",
    }
    assert all(hit.payload["programme_slug"] == "msc-data-science" for hit in data_science)

    computer_science = store.search(
        query, university_slug="uni-alpha", programme_slug="msc-computer-science", limit=10
    )
    assert {hit.payload["chunk_id"] for hit in computer_science} == {"uni-alpha-cs::0000"}


def test_upsert_length_mismatch_raises() -> None:
    store = _store()
    store.ensure_collection(8, reset=True)

    with pytest.raises(ValueError, match="same length"):
        store.upsert_chunks([_chunk("uni-x::0000", "uni-x")], [])
