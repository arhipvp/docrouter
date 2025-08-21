from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Union
import csv

# Опциональные зависимости
try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - dependency missing
    fitz = None

try:
    from docx import Document
except ImportError:  # pragma: no cover - dependency missing
    Document = None

# OCR для изображений — модуль может отсутствовать
try:
    from .image_ocr import extract_text_image  # ожидается сигнатура (path: Path, language: str) -> str
except Exception:  # pragma: no cover - optional module
    extract_text_image = None  # type: ignore


# ---------- Парсеры для «текстовых» форматов ----------

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
    parts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            parts.append(page.get_text())
    return "\n".join(parts)


def extract_text_docx(path: Path) -> str:
    """Извлечение текста из DOCX (python-docx)."""
    if Document is None:
        raise RuntimeError("python-docx не установлен")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_csv(path: Path) -> str:
    """Извлечение текста из CSV (через csv.reader)."""
    lines: list[str] = []
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


# ---------- Входная точка с поддержкой OCR ----------

def extract_text(file_path: Union[str, Path], language: str = "eng") -> str:
    """
    Извлечь текст из поддерживаемого файла.

    Поддерживаемые форматы:
      - Текстовые: .txt, .md, .pdf, .docx, .csv
      - Изображения (OCR): .jpg, .jpeg  (через image_ocr.extract_text_image)

    :param file_path: путь к файлу.
    :param language: язык OCR (ISO-коды tesseract, напр. 'eng', 'rus', 'deu').
    :return: извлечённый текст.
    :raises ValueError: если расширение не поддерживается.
    :raises RuntimeError: если требуемая зависимость для формата не установлена.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    # Ветвь для изображений — нужен отдельный параметр language
    if ext in {".jpg", ".jpeg"}:
        if extract_text_image is None:
            raise RuntimeError("Модуль OCR недоступен: .image_ocr.extract_text_image не найден")
        return extract_text_image(path, language=language)

    # Обычные «текстовые» форматы
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(f"Unsupported/unknown file extension: {ext}")
    return parser(path)


__all__ = [
    "extract_text",
    "extract_text_txt",
    "extract_text_md",
    "extract_text_pdf",
    "extract_text_docx",
    "extract_text_csv",
]
