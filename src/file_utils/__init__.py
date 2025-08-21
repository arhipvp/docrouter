from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

import csv

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - dependency missing
    fitz = None

try:
    from docx import Document
except ImportError:  # pragma: no cover - dependency missing
    Document = None


def extract_text_txt(path: Path) -> str:
    """Извлечение текста из .txt файла."""
    return path.read_text(encoding="utf-8")


def extract_text_md(path: Path) -> str:
    """Извлечение текста из .md файла."""
    return path.read_text(encoding="utf-8")


def extract_text_pdf(path: Path) -> str:
    """Извлечение текста из PDF с помощью PyMuPDF."""
    if fitz is None:
        raise RuntimeError("PyMuPDF не установлен")
    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def extract_text_docx(path: Path) -> str:
    """Извлечение текста из DOCX."""
    if Document is None:
        raise RuntimeError("python-docx не установлен")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_csv(path: Path) -> str:
    """Извлечение текста из CSV."""
    lines = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            lines.append(",".join(row))
    return "\n".join(lines)


_PARSERS: Dict[str, Callable[[Path], str]] = {
    ".txt": extract_text_txt,
    ".md": extract_text_md,
    ".pdf": extract_text_pdf,
    ".docx": extract_text_docx,
    ".csv": extract_text_csv,
}


def extract_text(path: Path) -> str:
    """Определяет парсер по расширению и извлекает текст."""
    ext = path.suffix.lower()
    if ext not in _PARSERS:
        raise ValueError(f"Неизвестное расширение файла: {ext}")
    return _PARSERS[ext](path)


__all__ = [
    "extract_text",
    "extract_text_txt",
    "extract_text_md",
    "extract_text_pdf",
    "extract_text_docx",
    "extract_text_csv",
]
