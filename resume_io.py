"""從上傳的檔案抽取文字（PDF / DOCX / 純文字）。"""
from __future__ import annotations

import io

import pypdf
import docx


def extract_bytes(data: bytes, filename: str) -> str:
    """從 bytes 抽取文字（供 FastAPI 上傳檔案用）。"""
    name = filename.lower()
    if name.endswith(".pdf"):
        return _pdf(io.BytesIO(data))
    if name.endswith(".docx"):
        return _docx(io.BytesIO(data))
    return data.decode("utf-8", errors="ignore")


def extract_text(file) -> str:
    """從 Streamlit 上傳物件抽取文字（保留給 app.py 舊版）。"""
    return extract_bytes(file.getvalue(), file.name)


def _pdf(buf) -> str:
    reader = pypdf.PdfReader(buf)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _docx(buf) -> str:
    d = docx.Document(buf)
    return "\n".join(p.text for p in d.paragraphs)
