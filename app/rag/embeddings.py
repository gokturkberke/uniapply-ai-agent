"""Embedding backends behind a model-agnostic protocol.

A deterministic ``FakeEmbedder`` keeps tests fully offline; ``FastEmbedEmbedder``
wraps fastembed (ONNX multilingual) for real use and is lazily loaded so importing
this module never downloads a model. The model id is pinned via settings for
reproducibility.
"""

import hashlib
import math
from typing import Protocol

from app.core.config import Settings, get_settings


class Embedder(Protocol):
    """Maps text to dense vectors. Implementations must be deterministic."""

    @property
    def model_id(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FakeEmbedder:
    """Deterministic, offline embedder for tests (hash-based, L2-normalized)."""

    model_id = "fake"

    def __init__(self, dimension: int = 32) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self._dimension:
            digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
            for byte in digest:
                values.append(byte / 255.0)
                if len(values) >= self._dimension:
                    break
            counter += 1
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class FastEmbedEmbedder:
    """fastembed (ONNX) multilingual embedder, lazily loaded on first embed call."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self._model = None

    def _get_model(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_id)
        return self._model

    @property
    def dimension(self) -> int:
        from fastembed import TextEmbedding

        for model in TextEmbedding.list_supported_models():
            if model["model"] == self.model_id:
                return int(model["dim"])
        raise ValueError(f"unknown fastembed model: {self.model_id!r}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._get_model().embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def get_embedder(settings: Settings | None = None) -> Embedder:
    """Return the embedder selected by ``embedding_provider``."""

    settings = settings or get_settings()
    if settings.embedding_provider == "fake":
        return FakeEmbedder()
    if settings.embedding_provider == "fastembed":
        return FastEmbedEmbedder(settings.embedding_model)
    raise ValueError(f"unknown embedding_provider: {settings.embedding_provider!r}")
