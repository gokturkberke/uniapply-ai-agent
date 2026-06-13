"""Tests for the document parsers."""

from pathlib import Path

import pytest

from app.rag.parsers import parse_document, parse_html, parse_pdf

HTML_FIXTURE = Path(__file__).parent / "fixtures" / "ingestion" / "sample.html"


def test_parse_html_preserves_structure() -> None:
    markdown = parse_html(HTML_FIXTURE)

    assert "Language Requirements" in markdown
    assert "IELTS" in markdown
    assert "6.5" in markdown
    assert "Bachelor transcript" in markdown
    # Non-content tags are dropped before conversion.
    assert "Programmes" not in markdown  # from <nav>
    assert "analytics" not in markdown  # from <script>


def test_parse_pdf_extracts_text(tmp_path: Path) -> None:
    import pymupdf  # provided by pymupdf4llm's PyMuPDF dependency

    pdf_path = tmp_path / "tiny.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Application deadline is July 15.")
    doc.save(pdf_path)
    doc.close()

    markdown = parse_pdf(pdf_path)

    assert "Application deadline" in markdown


def test_parse_document_dispatches_html() -> None:
    assert "Language Requirements" in parse_document(HTML_FIXTURE)


def test_parse_document_rejects_unsupported_suffix(tmp_path: Path) -> None:
    unsupported = tmp_path / "notes.docx"
    unsupported.write_text("placeholder", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported document type"):
        parse_document(unsupported)
