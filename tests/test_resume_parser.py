"""Unit and file-format tests for PDF/DOCX resume extraction."""

from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfWriter

from app.utils.resume_parser import ResumeParseError, extract_resume_text


def make_docx() -> bytes:
    """Build a small in-memory DOCX resume fixture."""
    document = Document()
    document.add_paragraph("Alex Example - Python Developer")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Skills"
    table.cell(0, 1).text = "Python, SQL"
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def make_pdf(encrypted: bool = False) -> bytes:
    """Build a small in-memory PDF fixture."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    if encrypted:
        writer.encrypt("test-password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_extracts_docx_paragraphs_and_tables() -> None:
    """DOCX text includes paragraph content and table cells."""
    extracted = extract_resume_text("resume.docx", make_docx())

    assert "Alex Example - Python Developer" in extracted
    assert "Skills | Python, SQL" in extracted


def test_rejects_unsupported_extension() -> None:
    """Only PDF and DOCX uploads are accepted."""
    with pytest.raises(ResumeParseError, match="PDF or DOCX"):
        extract_resume_text("resume.txt", b"resume text")


def test_rejects_empty_file() -> None:
    """Empty uploads are rejected before parsing."""
    with pytest.raises(ResumeParseError, match="uploaded resume is empty"):
        extract_resume_text("resume.pdf", b"")


def test_rejects_upload_above_size_limit() -> None:
    """Oversized uploads are rejected before parser invocation."""
    with pytest.raises(ResumeParseError, match="size limit of 10 bytes"):
        extract_resume_text("resume.pdf", b"x" * 11, max_file_bytes=10)


def test_rejects_invalid_pdf() -> None:
    """Malformed PDF bytes produce a user-safe parser error."""
    with pytest.raises(ResumeParseError, match="could not be read"):
        extract_resume_text("resume.pdf", b"not a pdf")


def test_rejects_encrypted_pdf() -> None:
    """Encrypted PDFs are explicitly unsupported."""
    with pytest.raises(ResumeParseError, match="Encrypted PDFs"):
        extract_resume_text("resume.pdf", make_pdf(encrypted=True))


def test_rejects_pdf_without_selectable_text() -> None:
    """Image-only or blank PDFs fail clearly because OCR is unavailable."""
    with pytest.raises(ResumeParseError, match="No selectable text"):
        extract_resume_text("resume.pdf", make_pdf())


def test_rejects_docx_with_excessive_expanded_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOCX archive expansion is bounded before document parsing."""
    monkeypatch.setattr("app.utils.resume_parser.MAX_DOCX_EXPANDED_BYTES", 1)

    with pytest.raises(ResumeParseError, match="contents exceed"):
        extract_resume_text("resume.docx", make_docx())


def test_rejects_extracted_text_above_character_limit() -> None:
    """Parsed document text is bounded before it reaches the AI service."""
    with pytest.raises(ResumeParseError, match="5-character limit"):
        extract_resume_text("resume.docx", make_docx(), max_text_chars=5)


def test_rejects_pdf_above_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF documents beyond the configured page ceiling are rejected."""
    monkeypatch.setattr("app.utils.resume_parser.MAX_PDF_PAGES", 0)

    with pytest.raises(ResumeParseError, match="limited to 0 pages"):
        extract_resume_text("resume.pdf", make_pdf())
