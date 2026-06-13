"""Dense retrieval with metadata pre-filtering and a Retrieval Gate.

Embeds a query, runs a scope-filtered dense search over the vector store, and
applies a Retrieval Gate: when the top hit's score is below ``retrieval_min_score``
the result is flagged as insufficient context (the deterministic refusal signal
that Phase 5 generation acts on). ``retrieve`` requires ``university_slug`` so the
anti-blending rule is enforced at the boundary.

Scope of this phase: retrieval only. No parent-document expansion, no hybrid /
rerank, no LLM, no endpoints.
"""

from pydantic import BaseModel

from app.core.config import get_settings
from app.rag.embeddings import Embedder, get_embedder
from app.rag.metadata import Chunk
from app.rag.vector_store import VectorStore


class RetrievedChunk(BaseModel):
    """A chunk returned from search, with its similarity score."""

    chunk: Chunk
    score: float


class RetrievalResult(BaseModel):
    """Outcome of a retrieval call, including the Retrieval Gate decision."""

    query: str
    university_slug: str
    programme_slug: str | None
    hits: list[RetrievedChunk]
    sufficient_context: bool
    top_score: float | None


def retrieve(
    query: str,
    *,
    university_slug: str,
    programme_slug: str | None = None,
    top_k: int | None = None,
    min_score: float | None = None,
    embedder: Embedder | None = None,
    vector_store: VectorStore | None = None,
) -> RetrievalResult:
    """Retrieve scope-filtered chunks for a query and apply the Retrieval Gate."""

    settings = get_settings()
    if top_k is None:
        top_k = settings.retrieval_top_k
    if min_score is None:
        min_score = settings.retrieval_min_score
    if embedder is None:
        embedder = get_embedder(settings)
    if vector_store is None:
        vector_store = VectorStore.from_settings()

    points = vector_store.search(
        embedder.embed_query(query),
        university_slug=university_slug,
        programme_slug=programme_slug,
        limit=top_k,
    )
    hits = [
        RetrievedChunk(chunk=Chunk.model_validate(point.payload), score=point.score)
        for point in points
    ]
    top_score = hits[0].score if hits else None
    sufficient_context = top_score is not None and top_score >= min_score

    return RetrievalResult(
        query=query,
        university_slug=university_slug,
        programme_slug=programme_slug,
        hits=hits,
        sufficient_context=sufficient_context,
        top_score=top_score,
    )
