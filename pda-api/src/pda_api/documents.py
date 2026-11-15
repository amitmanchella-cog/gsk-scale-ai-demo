"""Turn an uploaded .txt or .docx file into plain text."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePath
from zipfile import BadZipFile

from docx import Document

SUPPORTED_SUFFIXES = {".txt", ".md", ".docx"}


class UnsupportedDocumentError(ValueError):
    pass


def read_document(filename: str, content: bytes) -> str:
    suffix = PurePath(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedDocumentError(f"Unsupported file type '{suffix or filename}'. Upload a .txt or .docx file.")
    if suffix == ".docx":
        try:
            doc = Document(BytesIO(content))
        except (BadZipFile, KeyError, ValueError) as exc:
            raise UnsupportedDocumentError("The .docx file could not be read.") from exc
        lines = [paragraph.text for paragraph in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                lines.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(lines)
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")
