"""Tests for the deterministic fake embedder (offline)."""

from app.rag.embeddings import FakeEmbedder


def test_fake_embedder_is_deterministic() -> None:
    embedder = FakeEmbedder()

    assert embedder.embed_query("hallo welt") == embedder.embed_query("hallo welt")


def test_fake_embedder_dimension_and_batch() -> None:
    embedder = FakeEmbedder(dimension=16)

    vectors = embedder.embed_texts(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(len(vector) == 16 for vector in vectors)
    assert embedder.dimension == 16


def test_fake_embedder_distinct_texts_differ() -> None:
    embedder = FakeEmbedder()

    assert embedder.embed_query("english text") != embedder.embed_query("deutscher text")


def test_fake_embedder_is_l2_normalized() -> None:
    vector = FakeEmbedder(dimension=16).embed_query("normalize me")

    assert abs(sum(value * value for value in vector) - 1.0) < 1e-9
