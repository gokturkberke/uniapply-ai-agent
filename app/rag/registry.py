"""Curated source registry: load and query the declarative source manifest.

The manifest holds metadata only (pointers to official sources), never the
source documents themselves. Queries are scoped by university/programme so that
later retrieval can never blend requirements across institutions.
"""

import json
import re
from pathlib import Path

from app.core.config import get_settings
from app.rag.metadata import ProgrammeSummary, RegisteredSource, SourceAuthority

_TRAILING_PARENS = re.compile(r"\s*\([^)]*\)\s*$")


def load_registry(path: Path | None = None) -> list[RegisteredSource]:
    """Load and validate the source manifest into typed records.

    Resolves ``path`` from settings when not given. Raises ``ValueError`` on
    malformed JSON, a non-list payload, or a duplicate ``source_id``; invalid
    entries raise Pydantic's ``ValidationError``. An empty manifest is valid and
    yields an empty list.
    """

    manifest_path = path or Path(get_settings().registry_path)
    raw_text = manifest_path.read_text(encoding="utf-8")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"registry manifest {manifest_path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(payload, list):
        raise ValueError(
            f"registry manifest {manifest_path} must contain a JSON array of sources"
        )

    sources = [RegisteredSource.model_validate(entry) for entry in payload]

    seen: set[str] = set()
    for source in sources:
        if source.source_id in seen:
            raise ValueError(f"duplicate source_id in registry: {source.source_id!r}")
        seen.add(source.source_id)

    return sources


def filter_sources(
    sources: list[RegisteredSource],
    *,
    university_slug: str | None = None,
    programme_slug: str | None = None,
    source_authority: SourceAuthority | None = None,
) -> list[RegisteredSource]:
    """Return the sources matching every provided filter (pure function)."""

    result = sources
    if university_slug is not None:
        result = [s for s in result if s.university_slug == university_slug]
    if programme_slug is not None:
        result = [s for s in result if s.programme_slug == programme_slug]
    if source_authority is not None:
        result = [s for s in result if s.source_authority == source_authority]
    return list(result)


def distinct_programmes(sources: list[RegisteredSource]) -> list[ProgrammeSummary]:
    """Return the distinct (university, programme) pairs with a display title.

    Sources without a ``programme_slug`` are excluded. The title is the programme's
    ``primary`` source title (else the first source's), with a trailing parenthetical
    stripped (e.g. ``"... (programme page)"``). Sorted by ``(university_slug,
    programme_slug)`` for determinism.
    """

    grouped: dict[tuple[str, str], list[RegisteredSource]] = {}
    for source in sources:
        if source.programme_slug is None:
            continue
        key = (source.university_slug, source.programme_slug)
        grouped.setdefault(key, []).append(source)

    summaries: list[ProgrammeSummary] = []
    for (university_slug, programme_slug), group in grouped.items():
        primary = next(
            (s for s in group if s.source_authority == SourceAuthority.primary),
            group[0],
        )
        title = _TRAILING_PARENS.sub("", primary.title).strip()
        summaries.append(
            ProgrammeSummary(
                university_slug=university_slug,
                programme_slug=programme_slug,
                title=title,
            )
        )
    return sorted(summaries, key=lambda p: (p.university_slug, p.programme_slug))
