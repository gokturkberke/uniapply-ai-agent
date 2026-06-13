"""Structure-aware chunking: normalized Markdown -> parents + searchable chunks.

The chunker is offline, pure, and deterministic. It splits Markdown on headers
(parent-document pattern: each header section is a parent; child chunks reference
it), bounds chunk size by an approximate token estimate, and overlaps consecutive
chunks of an oversized section. Token counts are a documented approximation
(whitespace word count) until the embedding tokenizer is wired in (Phase 3b).
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from app.core.config import get_settings
from app.rag.metadata import Chunk, ChunkingResult, ParentSection, RegisteredSource
from app.rag.registry import load_registry

STATUS_CHUNKED = "chunked"
STATUS_SKIPPED_NOT_NORMALIZED = "skipped_not_normalized"

_HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Section:
    """A header-bounded slice of Markdown with its heading breadcrumb."""

    heading_path: list[str]
    text: str


class ChunkSummary(BaseModel):
    """Per-source outcome recorded in the chunk manifest."""

    source_id: str
    status: str
    chunk_count: int
    parent_count: int
    chunk_path: str | None


def estimate_tokens(text: str) -> int:
    """Approximate token count via whitespace word count (pluggable proxy)."""

    return len(text.split())


def split_into_sections(markdown: str) -> list[Section]:
    """Split Markdown into header-bounded sections with heading breadcrumbs.

    Content before the first header becomes a section with an empty heading path.
    The heading path is the full ancestor chain (e.g. h1 -> h2 -> h3).
    """

    sections: list[Section] = []
    heading_stack: list[tuple[int, str]] = []
    body_lines: list[str] = []
    current_path: list[str] = []

    def flush() -> None:
        text = "\n".join(body_lines).strip()
        if text:
            sections.append(Section(heading_path=list(current_path), text=text))

    for line in markdown.splitlines():
        match = _HEADER_PATTERN.match(line)
        if match is None:
            body_lines.append(line)
            continue
        flush()
        body_lines = []
        level = len(match.group(1))
        title = match.group(2).strip()
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, title))
        current_path = [title for _, title in heading_stack]

    flush()
    return sections


def _resolve_sizing(max_tokens: int | None, overlap_tokens: int | None) -> tuple[int, int]:
    if max_tokens is None or overlap_tokens is None:
        settings = get_settings()
        if max_tokens is None:
            max_tokens = settings.chunk_max_tokens
        if overlap_tokens is None:
            overlap_tokens = settings.chunk_overlap_tokens
    if overlap_tokens >= max_tokens:
        raise ValueError("chunk_overlap_tokens must be smaller than chunk_max_tokens")
    return max_tokens, overlap_tokens


def _split_oversized(text: str, *, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split an over-budget section into overlapping word windows.

    Each window holds at most ``max_tokens`` words; consecutive windows share
    ``overlap_tokens`` words. Word-level windowing guarantees both the size bound
    and a deterministic overlap (paragraph structure within an oversized section
    is not preserved; sections that fit are kept verbatim by the caller).
    """

    words = text.split()
    step = max_tokens - overlap_tokens
    windows: list[str] = []
    start = 0
    while start < len(words):
        windows.append(" ".join(words[start : start + max_tokens]))
        if start + max_tokens >= len(words):
            break
        start += step
    return windows


def chunk_markdown(
    markdown: str,
    source: RegisteredSource,
    *,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
    token_estimator: Callable[[str], int] = estimate_tokens,
) -> ChunkingResult:
    """Chunk normalized Markdown into parents and searchable child chunks."""

    max_tokens, overlap_tokens = _resolve_sizing(max_tokens, overlap_tokens)
    sections = split_into_sections(markdown)

    parents: list[ParentSection] = []
    chunks: list[Chunk] = []
    chunk_index = 0

    for section_index, section in enumerate(sections):
        parent_id = f"{source.source_id}::section::{section_index:03d}"
        parents.append(
            ParentSection(
                parent_id=parent_id,
                source_id=source.source_id,
                heading_path=section.heading_path,
                text=section.text,
            )
        )

        if token_estimator(section.text) <= max_tokens:
            texts = [section.text]
        else:
            texts = _split_oversized(
                section.text, max_tokens=max_tokens, overlap_tokens=overlap_tokens
            )

        for text in texts:
            chunks.append(
                Chunk(
                    chunk_id=f"{source.source_id}::{chunk_index:04d}",
                    parent_id=parent_id,
                    source_id=source.source_id,
                    university_slug=source.university_slug,
                    programme_slug=source.programme_slug,
                    source_authority=source.source_authority,
                    lang=source.lang,
                    country_scope=source.country_scope,
                    heading_path=section.heading_path,
                    text=text,
                    token_estimate=token_estimator(text),
                )
            )
            chunk_index += 1

    return ChunkingResult(source_id=source.source_id, parents=parents, chunks=chunks)


def chunk_source(
    source: RegisteredSource,
    *,
    normalized_dir: Path,
    chunk_dir: Path,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> ChunkingResult:
    """Chunk one source's normalized Markdown and write its JSON artifact."""

    normalized_path = normalized_dir / f"{source.source_id}.md"
    if not normalized_path.is_file():
        raise FileNotFoundError(
            f"normalized file for source {source.source_id!r} not found: {normalized_path}"
        )

    result = chunk_markdown(
        normalized_path.read_text(encoding="utf-8"),
        source,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )

    chunk_dir.mkdir(parents=True, exist_ok=True)
    (chunk_dir / f"{source.source_id}.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )
    return result


def chunk_corpus(
    sources: list[RegisteredSource] | None = None,
    *,
    normalized_dir: Path | None = None,
    chunk_dir: Path | None = None,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[ChunkSummary]:
    """Chunk every registered source that has a normalized file; write a manifest."""

    settings = get_settings()
    if sources is None:
        sources = load_registry()
    if normalized_dir is None:
        normalized_dir = Path(settings.normalized_dir)
    if chunk_dir is None:
        chunk_dir = Path(settings.chunk_dir)

    summaries: list[ChunkSummary] = []
    for source in sources:
        if not (normalized_dir / f"{source.source_id}.md").is_file():
            summaries.append(
                ChunkSummary(
                    source_id=source.source_id,
                    status=STATUS_SKIPPED_NOT_NORMALIZED,
                    chunk_count=0,
                    parent_count=0,
                    chunk_path=None,
                )
            )
            continue
        result = chunk_source(
            source,
            normalized_dir=normalized_dir,
            chunk_dir=chunk_dir,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )
        summaries.append(
            ChunkSummary(
                source_id=source.source_id,
                status=STATUS_CHUNKED,
                chunk_count=len(result.chunks),
                parent_count=len(result.parents),
                chunk_path=str(chunk_dir / f"{source.source_id}.json"),
            )
        )

    if summaries:
        chunk_dir.mkdir(parents=True, exist_ok=True)
        (chunk_dir / "manifest.json").write_text(
            json.dumps([summary.model_dump() for summary in summaries], indent=2),
            encoding="utf-8",
        )

    return summaries
