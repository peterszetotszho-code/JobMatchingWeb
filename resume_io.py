"""從上傳的檔案抽取文字（PDF / DOCX / 純文字）。"""
from __future__ import annotations

import io

import pypdf
import docx


def extract_text(file) -> str:
    name = file.name.lower()
    if name.endswith(".pdf"):
        return _from_pdf(file)
    if name.endswith(".docx"):
        return _from_docx(file)
    # 其餘視為純文字
    return file.getvalue().decode("utf-8", errors="ignore")


def _from_pdf(file) -> str:
    reader = pypdf.PdfReader(io.BytesIO(file.getvalue()))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _from_docx(file) -> str:
    d = docx.Document(io.BytesIO(file.getvalue()))
    return "\n".join(p.text for p in d.paragraphs)
