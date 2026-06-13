"""Offline ingestion: normalize registered raw sources into Markdown.

This is the ingestion lane. It reads manually-downloaded files from the raw
archive, converts them to Markdown via :mod:`app.rag.parsers`, and writes the
result to the normalized layer. It never fetches from the network and never
fabricates metadata such as ``last_updated`` (that is user-curated and read-only
here).
"""

import json
from pathlib import Path

from pydantic import BaseModel

from app.core.config import get_settings
from app.rag.metadata import RegisteredSource
from app.rag.parsers import parse_document
from app.rag.registry import load_registry

STATUS_NORMALIZED = "normalized"
STATUS_SKIPPED_NO_LOCAL_PATH = "skipped_no_local_path"


class IngestionResult(BaseModel):
    """Outcome of normalizing one registered source."""

    source_id: str
    raw_path: str | None
    normalized_path: str | None
    parser: str | None
    char_count: int
    status: str


def normalize_source(
    source: RegisteredSource,
    *,
    raw_dir: Path,
    normalized_dir: Path,
) -> IngestionResult:
    """Normalize one registered source's raw file into Markdown.

    Sources without a ``local_path`` are reported as skipped. A registered
    ``local_path`` whose file is missing is a misconfiguration and raises
    ``FileNotFoundError``.
    """

    if source.local_path is None:
        return IngestionResult(
            source_id=source.source_id,
            raw_path=None,
            normalized_path=None,
            parser=None,
            char_count=0,
            status=STATUS_SKIPPED_NO_LOCAL_PATH,
        )

    raw_path = raw_dir / source.local_path
    if not raw_path.is_file():
        raise FileNotFoundError(
            f"raw file for source {source.source_id!r} not found: {raw_path}"
        )

    markdown = parse_document(raw_path)

    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = normalized_dir / f"{source.source_id}.md"
    normalized_path.write_text(markdown, encoding="utf-8")

    return IngestionResult(
        source_id=source.source_id,
        raw_path=str(raw_path),
        normalized_path=str(normalized_path),
        parser=raw_path.suffix.lower(),
        char_count=len(markdown),
        status=STATUS_NORMALIZED,
    )


def normalize_registry(
    sources: list[RegisteredSource] | None = None,
    *,
    raw_dir: Path | None = None,
    normalized_dir: Path | None = None,
) -> list[IngestionResult]:
    """Normalize every registered source and write a derived output manifest."""

    settings = get_settings()
    if sources is None:
        sources = load_registry()
    if raw_dir is None:
        raw_dir = Path(settings.raw_dir)
    if normalized_dir is None:
        normalized_dir = Path(settings.normalized_dir)

    results = [
        normalize_source(source, raw_dir=raw_dir, normalized_dir=normalized_dir)
        for source in sources
    ]

    if results:
        normalized_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = normalized_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps([result.model_dump() for result in results], indent=2),
            encoding="utf-8",
        )

    return results
