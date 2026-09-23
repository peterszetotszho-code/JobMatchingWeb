"""Extract text from uploaded files (PDF / DOCX / plain text)."""
from __future__ import annotations

import io

import pypdf
import docx


def extract_bytes(data: bytes, filename: str) -> str:
    """Extract text from bytes (used by the FastAPI upload endpoint)."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return _pdf(io.BytesIO(data))
    if name.endswith(".docx"):
        return _docx(io.BytesIO(data))
    return data.decode("utf-8", errors="ignore")


def extract_text(file) -> str:
    """Extract text from a Streamlit upload object (kept for the legacy app.py)."""
    return extract_bytes(file.getvalue(), file.name)


def _pdf(buf) -> str:
    reader = pypdf.PdfReader(buf)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _docx(buf) -> str:
    d = docx.Document(buf)
    return "\n".join(p.text for p in d.paragraphs)
