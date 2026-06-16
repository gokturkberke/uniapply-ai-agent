"""Qdrant vector store (local/embedded mode) for chunk vectors + metadata.

Wraps qdrant-client in local mode (on-disk or in-memory) so the index is fully
offline. The chunk's scoping fields live in the payload so search can pre-filter
by university/programme, carrying the anti-blending guarantee into retrieval.
"""

import uuid
from pathlib import Path

from qdrant_client import QdrantClient, models

from app.core.config import get_settings
from app.rag.metadata import Chunk

# Fixed namespace so a chunk_id always maps to the same Qdrant point id.
_POINT_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, chunk_id))


class VectorStore:
    """Thin wrapper over a Qdrant collection of chunk vectors."""

    def __init__(self, client: QdrantClient, collection: str) -> None:
        self._client = client
        self._collection = collection

    @classmethod
    def from_settings(cls, *, location: str | None = None) -> "VectorStore":
        settings = get_settings()
        if location is not None:
            client = QdrantClient(location=location)
        elif settings.qdrant_url:
            # Server mode (e.g. the Docker qdrant service); opt-in via QDRANT_URL.
            client = QdrantClient(url=settings.qdrant_url)
        else:
            # Default: embedded on-disk mode (local dev).
            Path(settings.qdrant_path).mkdir(parents=True, exist_ok=True)
            client = QdrantClient(path=settings.qdrant_path)
        return cls(client, settings.qdrant_collection)

    @property
    def collection(self) -> str:
        return self._collection

    def ensure_collection(self, dimension: int, *, reset: bool = False) -> None:
        exists = self._client.collection_exists(self._collection)
        if exists and reset:
            self._client.delete_collection(self._collection)
            exists = False
        if not exists:
            self._client.create_collection(
                self._collection,
                vectors_config=models.VectorParams(
                    size=dimension, distance=models.Distance.COSINE
                ),
            )

    def upsert_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        points = [
            models.PointStruct(
                id=_point_id(chunk.chunk_id),
                vector=vector,
                payload=chunk.model_dump(mode="json"),
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        if points:
            self._client.upsert(self._collection, points=points)
        return len(points)

    def search(
        self,
        vector: list[float],
        *,
        university_slug: str | None = None,
        programme_slug: str | None = None,
        limit: int = 5,
    ) -> list[models.ScoredPoint]:
        conditions: list[models.FieldCondition] = []
        if university_slug is not None:
            conditions.append(
                models.FieldCondition(
                    key="university_slug", match=models.MatchValue(value=university_slug)
                )
            )
        if programme_slug is not None:
            conditions.append(
                models.FieldCondition(
                    key="programme_slug", match=models.MatchValue(value=programme_slug)
                )
            )
        query_filter = models.Filter(must=conditions) if conditions else None
        response = self._client.query_points(
            self._collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return response.points

    def count(self) -> int:
        return self._client.count(self._collection).count
