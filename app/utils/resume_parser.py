"""Safe text extraction for supported resume document formats."""

from io import BytesIO
from pathlib import PurePath
from zipfile import ZipFile

from docx import Document
from pypdf import PdfReader

MAX_RESUME_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DOCX_EXPANDED_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 100
DEFAULT_MAX_TEXT_CHARS = 30000


def _format_size(byte_count: int) -> str:
    """Format a byte limit using the largest exact binary unit."""
    for unit, divisor in (("MB", 1024 * 1024), ("KB", 1024)):
        if byte_count >= divisor and byte_count % divisor == 0:
            return f"{byte_count // divisor} {unit}"
    return f"{byte_count} bytes"


class ResumeParseError(ValueError):
    """Raised when a resume file is unsupported, unsafe, or unreadable."""


def extract_resume_text(
    file_name: str,
    file_content: bytes,
    max_file_bytes: int = MAX_RESUME_UPLOAD_BYTES,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> str:
    """Extract text from a bounded PDF or DOCX upload."""
    suffix = PurePath(file_name).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise ResumeParseError("Upload a PDF or DOCX resume.")
    if not file_content:
        raise ResumeParseError("The uploaded resume is empty.")
    if len(file_content) > max_file_bytes:
        raise ResumeParseError(
            "The uploaded resume exceeds the size limit of "
            f"{_format_size(max_file_bytes)}."
        )
    if max_text_chars < 1:
        raise ValueError("max_text_chars must be greater than zero.")

    try:
        if suffix == ".pdf":
            text = _extract_pdf_text(file_content)
        else:
            text = _extract_docx_text(file_content)
    except ResumeParseError:
        raise
    except Exception:
        raise ResumeParseError(
            "The uploaded resume could not be read. Check that it is a valid, "
            "unencrypted PDF or DOCX file."
        ) from None

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ResumeParseError(
            "No selectable text was found. Scanned PDFs require OCR, which is not "
            "supported."
        )
    if len(cleaned_text) > max_text_chars:
        raise ResumeParseError(
            f"Extracted resume text exceeds the {max_text_chars:,}-character limit."
        )
    return cleaned_text


def _extract_pdf_text(file_content: bytes) -> str:
    """Extract text from each page of a PDF document."""
    reader = PdfReader(BytesIO(file_content), strict=False)
    if reader.is_encrypted:
        raise ResumeParseError("Encrypted PDFs are not supported.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ResumeParseError(f"PDF resumes are limited to {MAX_PDF_PAGES} pages.")
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(file_content: bytes) -> str:
    """Extract paragraphs and table cells from a size-bounded DOCX archive."""
    with ZipFile(BytesIO(file_content)) as archive:
        expanded_size = sum(entry.file_size for entry in archive.infolist())
        if expanded_size > MAX_DOCX_EXPANDED_BYTES:
            raise ResumeParseError("The DOCX contents exceed the supported size limit.")

    document = Document(BytesIO(file_content))
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)
