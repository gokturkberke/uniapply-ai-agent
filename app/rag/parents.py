"""Parent-section lookup for the parent-document retrieval pattern.

Parent sections are not stored in the vector index; they live in the chunk
artifacts (``data/chunks/<source_id>.json`` = ``ChunkingResult`` with ``parents``).
``ParentStore`` loads them lazily, one source file at a time and cached, so only
the sources actually referenced by retrieval hits are read into memory.
"""

from pathlib import Path

from app.core.config import get_settings
from app.rag.metadata import ChunkingResult, ParentSection


class ParentStore:
    """Lazy, cached lookup of parent sections from chunk artifacts."""

    def __init__(self, chunk_dir: Path) -> None:
        self._chunk_dir = chunk_dir
        self._cache: dict[str, dict[str, ParentSection]] = {}

    @classmethod
    def from_settings(cls) -> "ParentStore":
        return cls(Path(get_settings().chunk_dir))

    def _load_source(self, source_id: str) -> dict[str, ParentSection]:
        if source_id not in self._cache:
            path = self._chunk_dir / f"{source_id}.json"
            if path.is_file():
                result = ChunkingResult.model_validate_json(path.read_text(encoding="utf-8"))
                self._cache[source_id] = {
                    parent.parent_id: parent for parent in result.parents
                }
            else:
                self._cache[source_id] = {}
        return self._cache[source_id]

    def get(self, source_id: str, parent_id: str) -> ParentSection | None:
        return self._load_source(source_id).get(parent_id)
