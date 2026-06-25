from pathlib import Path

import fitz
from docx import Document as DocxDocument

from app.text_processing import normalize_text


def extract_text(path: Path, file_type: str) -> list[tuple[int | None, str]]:
    suffix = file_type.lower().lstrip(".")
    if suffix == "pdf":
        return extract_pdf(path)
    if suffix == "docx":
        return extract_docx(path)
    if suffix == "txt":
        return extract_txt(path)
    raise ValueError(f"Unsupported file type: {file_type}")


def extract_pdf(path: Path) -> list[tuple[int | None, str]]:
    pages: list[tuple[int | None, str]] = []
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            text = normalize_text(page.get_text("text"))
            if text:
                pages.append((page_index, text))
    return pages


def extract_docx(path: Path) -> list[tuple[int | None, str]]:
    doc = DocxDocument(path)
    parts = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
    return [(None, normalize_text("\n\n".join(parts)))] if parts else []


def extract_txt(path: Path) -> list[tuple[int | None, str]]:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            return [(None, normalize_text(path.read_text(encoding=encoding)))]
        except UnicodeDecodeError:
            continue
    return [(None, normalize_text(path.read_text(encoding="utf-8", errors="ignore")))]
