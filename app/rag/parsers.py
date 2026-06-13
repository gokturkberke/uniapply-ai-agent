"""Document parsers: normalize a single raw file into Markdown.

Dispatch is by file suffix so a format's backend can be swapped without touching
callers (e.g. a Docling backend can later replace ``parse_pdf``). The parsers are
offline and pure: each reads one local file and returns Markdown, preserving the
structural elements (headings, tables, lists) that admission requirements rely on.
"""

from collections.abc import Callable
from pathlib import Path

import pymupdf4llm
from bs4 import BeautifulSoup
from markdownify import markdownify

_STRIP_TAGS = ("script", "style", "nav")


def parse_pdf(path: Path) -> str:
    """Convert a PDF to Markdown, preserving headings and tables."""

    return pymupdf4llm.to_markdown(str(path))


def parse_html(path: Path) -> str:
    """Convert an HTML file to Markdown after dropping non-content tags."""

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(list(_STRIP_TAGS)):
        tag.decompose()
    return markdownify(str(soup))


_PARSERS_BY_SUFFIX: dict[str, Callable[[Path], str]] = {
    ".pdf": parse_pdf,
    ".html": parse_html,
    ".htm": parse_html,
}


def parse_document(path: Path) -> str:
    """Normalize a raw document to Markdown, dispatching on its suffix."""

    parser = _PARSERS_BY_SUFFIX.get(path.suffix.lower())
    if parser is None:
        raise ValueError(f"unsupported document type: {path.suffix!r}")
    return parser(path)
