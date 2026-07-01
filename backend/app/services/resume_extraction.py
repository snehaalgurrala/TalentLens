"""
Pure text extraction from PDF, DOCX, and ZIP files.

No database access. No AI calls. No HTTP layer.
All public async functions delegate blocking I/O to asyncio.to_thread so they
are safe to call from any async context.
"""

import asyncio
import io
import zipfile
from pathlib import Path

_DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
_ALL_SUPPORTED = {".pdf", ".docx", ".zip"}


class ExtractionError(Exception):
    """Raised when a file cannot be read or its text cannot be extracted."""


def detect_file_type(filename: str) -> str:
    """Return 'pdf', 'docx', or 'zip'. Raises ValueError for anything else."""
    ext = Path(filename).suffix.lower()
    if ext not in _ALL_SUPPORTED:
        supported = ", ".join(sorted(e.lstrip(".").upper() for e in _ALL_SUPPORTED))
        raise ValueError(
            f"Unsupported file type '{ext or '(none)'}' in '{filename}'. "
            f"Supported: {supported}."
        )
    return ext.lstrip(".")


# ── Synchronous inner implementations ────────────────────────────────────────
# Called via asyncio.to_thread — must not themselves be async.


def _extract_pdf_bytes(data: bytes, name: str) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except PdfReadError as exc:
        raise ExtractionError(f"Could not read PDF '{name}': {exc}") from exc
    except Exception as exc:
        raise ExtractionError(f"Unexpected error reading PDF '{name}': {exc}") from exc


def _extract_docx_bytes(data: bytes, name: str) -> str:
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    try:
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except (PackageNotFoundError, zipfile.BadZipFile) as exc:
        raise ExtractionError(f"Could not read DOCX '{name}': {exc}") from exc
    except Exception as exc:
        raise ExtractionError(f"Unexpected error reading DOCX '{name}': {exc}") from exc


def _read_and_extract_pdf(file_path: str) -> str:
    with open(file_path, "rb") as fh:
        return _extract_pdf_bytes(fh.read(), file_path)


def _read_and_extract_docx(file_path: str) -> str:
    with open(file_path, "rb") as fh:
        return _extract_docx_bytes(fh.read(), file_path)


def _read_and_extract_zip(file_path: str) -> list[tuple[str, str]]:
    try:
        zf = zipfile.ZipFile(file_path)
    except zipfile.BadZipFile as exc:
        raise ExtractionError(f"'{file_path}' is not a valid ZIP file.") from exc

    results: list[tuple[str, str]] = []
    with zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue

            # Use only the basename to prevent path traversal
            name = Path(entry.filename).name
            ext = Path(name).suffix.lower()

            if ext == ".zip":
                raise ExtractionError(
                    f"Nested ZIP files are not supported "
                    f"(found '{entry.filename}' inside '{file_path}')."
                )
            if ext not in _DOCUMENT_EXTENSIONS:
                continue  # .txt, .png, etc. — skip silently

            data = zf.read(entry.filename)
            if ext == ".pdf":
                text = _extract_pdf_bytes(data, name)
            else:
                text = _extract_docx_bytes(data, name)
            results.append((name, text))

    return results


# ── Public async API ──────────────────────────────────────────────────────────


async def extract_text_from_pdf(file_path: str) -> str:
    """Read a PDF from disk and return its extracted text."""
    return await asyncio.to_thread(_read_and_extract_pdf, file_path)


async def extract_text_from_docx(file_path: str) -> str:
    """Read a DOCX from disk and return its extracted text."""
    return await asyncio.to_thread(_read_and_extract_docx, file_path)


async def extract_text_from_zip(file_path: str) -> list[tuple[str, str]]:
    """
    Extract text from every PDF/DOCX inside a ZIP.

    Returns a list of (filename, extracted_text) pairs — one entry per
    supported file found. Returns an empty list if the ZIP has no supported
    files. Unsupported extensions are skipped silently.

    Raises ExtractionError if:
    - The file is not a valid ZIP archive.
    - A nested ZIP entry is encountered.
    - Any contained PDF or DOCX cannot be parsed.
    """
    return await asyncio.to_thread(_read_and_extract_zip, file_path)


async def extract_text_from_pdf_bytes(data: bytes, filename: str = "upload.pdf") -> str:
    """Extract text from in-memory PDF bytes (no file on disk required)."""
    return await asyncio.to_thread(_extract_pdf_bytes, data, filename)


async def extract_text_from_docx_bytes(data: bytes, filename: str = "upload.docx") -> str:
    """Extract text from in-memory DOCX bytes (no file on disk required)."""
    return await asyncio.to_thread(_extract_docx_bytes, data, filename)
