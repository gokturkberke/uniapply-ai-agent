"""Tests for dense retrieval + the Retrieval Gate (offline)."""

import pytest
from qdrant_client import QdrantClient

from app.rag.embeddings import FakeEmbedder
from app.rag.metadata import Chunk, Language, SourceAuthority
from app.rag.retrieval import retrieve
from app.rag.vector_store import VectorStore

_EMBEDDER = FakeEmbedder()


def _chunk(chunk_id: str, university_slug: str, programme_slug: str, text: str) -> Chunk:
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


def _seeded_store() -> VectorStore:
    store = VectorStore(QdrantClient(location=":memory:"), "retrieval_test")
    store.ensure_collection(_EMBEDDER.dimension, reset=True)
    chunks = [
        _chunk("uni-alpha-ds::0000", "uni-alpha", "msc-data-science", "alpha data science one"),
        _chunk("uni-alpha-ds::0001", "uni-alpha", "msc-data-science", "alpha data science two"),
        _chunk("uni-alpha-cs::0000", "uni-alpha", "msc-computer-science", "alpha computer science"),
        _chunk("uni-beta-ds::0000", "uni-beta", "msc-data-science", "beta data science"),
    ]
    store.upsert_chunks(chunks, _EMBEDDER.embed_texts([c.text for c in chunks]))
    return store


def test_retrieve_isolates_by_university() -> None:
    result = retrieve(
        "question", university_slug="uni-alpha", min_score=-1.0,
        embedder=_EMBEDDER, vector_store=_seeded_store(),
    )

    assert result.hits
    assert all(hit.chunk.university_slug == "uni-alpha" for hit in result.hits)


def test_retrieve_isolates_by_programme_within_university() -> None:
    result = retrieve(
        "question", university_slug="uni-alpha", programme_slug="msc-data-science",
        min_score=-1.0, embedder=_EMBEDDER, vector_store=_seeded_store(),
    )

    assert {hit.chunk.chunk_id for hit in result.hits} == {
        "uni-alpha-ds::0000",
        "uni-alpha-ds::0001",
    }
    assert all(hit.chunk.programme_slug == "msc-data-science" for hit in result.hits)


def test_retrieve_respects_top_k() -> None:
    result = retrieve(
        "question", university_slug="uni-alpha", top_k=1, min_score=-1.0,
        embedder=_EMBEDDER, vector_store=_seeded_store(),
    )

    assert len(result.hits) == 1


def test_gate_passes_with_low_threshold() -> None:
    result = retrieve(
        "question", university_slug="uni-alpha", min_score=-1.0,
        embedder=_EMBEDDER, vector_store=_seeded_store(),
    )

    assert result.sufficient_context is True
    assert result.top_score is not None


def test_gate_refuses_with_unreachable_threshold() -> None:
    result = retrieve(
        "question", university_slug="uni-alpha", min_score=1.01,
        embedder=_EMBEDDER, vector_store=_seeded_store(),
    )

    assert result.sufficient_context is False  # cosine similarity never exceeds 1.0


def test_unknown_university_yields_empty_and_insufficient() -> None:
    result = retrieve(
        "question", university_slug="uni-unknown", min_score=-1.0,
        embedder=_EMBEDDER, vector_store=_seeded_store(),
    )

    assert result.hits == []
    assert result.sufficient_context is False
    assert result.top_score is None


def test_university_slug_is_required() -> None:
    with pytest.raises(TypeError):
        retrieve("question")  # type: ignore[call-arg]
