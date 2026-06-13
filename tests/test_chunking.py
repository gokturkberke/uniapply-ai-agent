"""Tests for structure-aware chunking."""

import json
from pathlib import Path

import pytest

from app.rag.chunking import (
    STATUS_CHUNKED,
    STATUS_SKIPPED_NOT_NORMALIZED,
    chunk_corpus,
    chunk_markdown,
    chunk_source,
    split_into_sections,
)
from app.rag.metadata import Language, RegisteredSource, SourceAuthority, SourceType

FIXTURE = Path(__file__).parent / "fixtures" / "chunking" / "sample_normalized.md"
APPLICATION_STEPS = ["Master Programme Overview", "Application Steps"]


def _make_source(source_id: str = "alpha-overview") -> RegisteredSource:
    return RegisteredSource(
        source_id=source_id,
        title="Synthetic source",
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        source_type=SourceType.official_page,
        source_authority=SourceAuthority.primary,
        lang=Language.en,
        url="https://example.org/alpha/data-science",
        country_scope=["all"],
        local_path=None,
    )


def test_split_into_sections_tracks_heading_path() -> None:
    paths = [s.heading_path for s in split_into_sections(FIXTURE.read_text(encoding="utf-8"))]

    assert [] in paths  # pre-header content
    assert ["Master Programme Overview", "Language Requirements", "Accepted certificates"] in paths
    assert APPLICATION_STEPS in paths


def test_small_section_is_single_verbatim_chunk() -> None:
    result = chunk_markdown(
        "## Tiny\n\nJust a few words here.",
        _make_source(),
        max_tokens=50,
        overlap_tokens=10,
    )

    tiny = [c for c in result.chunks if c.heading_path == ["Tiny"]]
    assert len(tiny) == 1
    assert tiny[0].text == "Just a few words here."


def test_oversized_section_splits_with_overlap() -> None:
    result = chunk_markdown(
        FIXTURE.read_text(encoding="utf-8"),
        _make_source(),
        max_tokens=20,
        overlap_tokens=5,
    )

    steps = [c for c in result.chunks if c.heading_path == APPLICATION_STEPS]
    assert len(steps) > 1
    for chunk in steps:
        assert chunk.token_estimate <= 20
    for earlier, later in zip(steps, steps[1:]):
        assert set(earlier.text.split()) & set(later.text.split())  # overlap


def test_chunk_ids_unique_ordered_and_linked() -> None:
    result = chunk_markdown(
        FIXTURE.read_text(encoding="utf-8"),
        _make_source(),
        max_tokens=20,
        overlap_tokens=5,
    )

    ids = [c.chunk_id for c in result.chunks]
    assert ids == sorted(ids)  # zero-padded ids sort in generation order
    assert len(set(ids)) == len(ids)
    parent_ids = {p.parent_id for p in result.parents}
    assert all(c.parent_id in parent_ids for c in result.chunks)


def test_scoping_fields_copied_from_source() -> None:
    result = chunk_markdown(
        FIXTURE.read_text(encoding="utf-8"),
        _make_source(),
        max_tokens=20,
        overlap_tokens=5,
    )

    assert result.chunks
    for chunk in result.chunks:
        assert chunk.university_slug == "uni-alpha"
        assert chunk.programme_slug == "msc-data-science"
        assert chunk.source_authority == SourceAuthority.primary
        assert chunk.lang == Language.en
        assert chunk.country_scope == ["all"]


def test_chunking_is_deterministic() -> None:
    markdown = FIXTURE.read_text(encoding="utf-8")
    source = _make_source()

    first = chunk_markdown(markdown, source, max_tokens=20, overlap_tokens=5)
    second = chunk_markdown(markdown, source, max_tokens=20, overlap_tokens=5)

    assert first.model_dump() == second.model_dump()


def test_overlap_must_be_smaller_than_max() -> None:
    with pytest.raises(ValueError, match="smaller than"):
        chunk_markdown("## H\n\nbody text", _make_source(), max_tokens=10, overlap_tokens=10)


def test_chunk_source_writes_artifact(tmp_path: Path) -> None:
    normalized_dir = tmp_path / "normalized"
    chunk_dir = tmp_path / "chunks"
    normalized_dir.mkdir()
    (normalized_dir / "alpha-overview.md").write_text(
        FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = chunk_source(
        _make_source("alpha-overview"),
        normalized_dir=normalized_dir,
        chunk_dir=chunk_dir,
        max_tokens=20,
        overlap_tokens=5,
    )

    artifact = chunk_dir / "alpha-overview.json"
    assert artifact.is_file()
    assert result.chunks
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["source_id"] == "alpha-overview"
    assert len(payload["chunks"]) == len(result.chunks)


def test_chunk_source_missing_normalized_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ghost"):
        chunk_source(
            _make_source("ghost"),
            normalized_dir=tmp_path / "normalized",
            chunk_dir=tmp_path / "chunks",
        )


def test_chunk_corpus_statuses_and_manifest(tmp_path: Path) -> None:
    normalized_dir = tmp_path / "normalized"
    chunk_dir = tmp_path / "chunks"
    normalized_dir.mkdir()
    (normalized_dir / "alpha-overview.md").write_text(
        FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )

    summaries = chunk_corpus(
        [_make_source("alpha-overview"), _make_source("beta-missing")],
        normalized_dir=normalized_dir,
        chunk_dir=chunk_dir,
        max_tokens=20,
        overlap_tokens=5,
    )

    status_by_id = {s.source_id: s.status for s in summaries}
    assert status_by_id["alpha-overview"] == STATUS_CHUNKED
    assert status_by_id["beta-missing"] == STATUS_SKIPPED_NOT_NORMALIZED
    manifest = chunk_dir / "manifest.json"
    assert manifest.is_file()
    assert len(json.loads(manifest.read_text(encoding="utf-8"))) == 2
