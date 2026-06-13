"""Tests for the ingestion normalization pipeline."""

import json
from pathlib import Path

import pytest

from app.rag.ingestion import (
    STATUS_NORMALIZED,
    STATUS_SKIPPED_NO_LOCAL_PATH,
    normalize_registry,
    normalize_source,
)
from app.rag.metadata import (
    Language,
    RegisteredSource,
    SourceAuthority,
    SourceType,
)

HTML_FIXTURE = Path(__file__).parent / "fixtures" / "ingestion" / "sample.html"


def _make_source(source_id: str, local_path: str | None) -> RegisteredSource:
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
        local_path=local_path,
    )


def _seed_raw_html(raw_dir: Path, filename: str) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / filename).write_text(
        HTML_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )


def test_normalize_source_writes_markdown(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    _seed_raw_html(raw_dir, "alpha.html")

    result = normalize_source(
        _make_source("alpha-ds-official", "alpha.html"),
        raw_dir=raw_dir,
        normalized_dir=normalized_dir,
    )

    assert result.status == STATUS_NORMALIZED
    assert result.char_count > 0
    out = normalized_dir / "alpha-ds-official.md"
    assert out.is_file()
    assert "Language Requirements" in out.read_text(encoding="utf-8")


def test_normalize_source_skips_when_no_local_path(tmp_path: Path) -> None:
    result = normalize_source(
        _make_source("no-file", None),
        raw_dir=tmp_path / "raw",
        normalized_dir=tmp_path / "normalized",
    )

    assert result.status == STATUS_SKIPPED_NO_LOCAL_PATH
    assert result.char_count == 0
    assert result.normalized_path is None


def test_normalize_source_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ghost"):
        normalize_source(
            _make_source("ghost", "absent.html"),
            raw_dir=tmp_path / "raw",
            normalized_dir=tmp_path / "normalized",
        )


def test_normalize_registry_writes_manifest(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    _seed_raw_html(raw_dir, "alpha.html")

    results = normalize_registry(
        [
            _make_source("alpha-ds-official", "alpha.html"),
            _make_source("beta-no-file", None),
        ],
        raw_dir=raw_dir,
        normalized_dir=normalized_dir,
    )

    assert {r.status for r in results} == {
        STATUS_NORMALIZED,
        STATUS_SKIPPED_NO_LOCAL_PATH,
    }
    manifest = normalized_dir / "manifest.json"
    assert manifest.is_file()
    assert len(json.loads(manifest.read_text(encoding="utf-8"))) == 2
