"""Tests for the parent-section store (offline, tmp artifacts)."""

from pathlib import Path

from app.rag.metadata import ChunkingResult, ParentSection
from app.rag.parents import ParentStore


def _write_artifact(chunk_dir: Path, source_id: str) -> None:
    chunk_dir.mkdir(parents=True, exist_ok=True)
    result = ChunkingResult(
        source_id=source_id,
        parents=[
            ParentSection(
                parent_id=f"{source_id}::section::000",
                source_id=source_id,
                heading_path=["Language Requirements"],
                text="Applicants must provide proof of English proficiency.",
            )
        ],
        chunks=[],
    )
    (chunk_dir / f"{source_id}.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )


def test_get_returns_parent(tmp_path: Path) -> None:
    _write_artifact(tmp_path, "alpha-src")
    store = ParentStore(tmp_path)

    parent = store.get("alpha-src", "alpha-src::section::000")

    assert parent is not None
    assert parent.heading_path == ["Language Requirements"]


def test_get_unknown_parent_id_returns_none(tmp_path: Path) -> None:
    _write_artifact(tmp_path, "alpha-src")
    store = ParentStore(tmp_path)

    assert store.get("alpha-src", "alpha-src::section::999") is None


def test_get_missing_source_file_returns_none(tmp_path: Path) -> None:
    store = ParentStore(tmp_path)

    assert store.get("ghost-src", "ghost-src::section::000") is None
