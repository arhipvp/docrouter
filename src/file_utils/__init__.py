from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Union
import csv
import logging
import tempfile
from PIL import Image, ImageOps
import requests

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME,
)

# Опциональные зависимости
try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - dependency missing
    fitz = None

try:
    from docx import Document
except ImportError:  # pragma: no cover - dependency missing
    Document = None

try:
    import xlrd
except ImportError:  # pragma: no cover - dependency missing
    xlrd = None

try:
    import openpyxl
except ImportError:  # pragma: no cover - dependency missing
    openpyxl = None

# OCR для изображений — модуль может отсутствовать
try:
    from .image_ocr import extract_text_image  # ожидается сигнатура (path: Path, language: str) -> str
except Exception:  # pragma: no cover - optional module
    extract_text_image = None  # type: ignore

from .mrz import parse_mrz

logger = logging.getLogger(__name__)


_PARSER_REGISTRY: Dict[str, Callable[[Path], str]] = {}


def register_parser(ext: str) -> Callable[[Callable[[Path], str]], Callable[[Path], str]]:
    """Декоратор для регистрации парсеров файлов."""

    def decorator(func: Callable[[Path], str]) -> Callable[[Path], str]:
        _PARSER_REGISTRY[ext.lower()] = func
        return func

    return decorator


# ---------- Парсеры для «текстовых» форматов ----------


@register_parser(".txt")
def extract_text_txt(path: Path) -> str:
    """Извлечение текста из .txt файла."""
    return path.read_text(encoding="utf-8")


@register_parser(".md")
def extract_text_md(path: Path) -> str:
    """Извлечение текста из .md файла."""
    return path.read_text(encoding="utf-8")


@register_parser(".pdf")
def extract_text_pdf(path: Path) -> str:
    """Извлечение текста из PDF с помощью PyMuPDF."""
    if fitz is None:
        raise RuntimeError("PyMuPDF не установлен")
    parts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            parts.append(page.get_text())
    return "\n".join(parts)


@register_parser(".docx")
def extract_text_docx(path: Path) -> str:
    """Извлечение текста из DOCX (python-docx)."""
    if Document is None:
        raise RuntimeError("python-docx не установлен")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


@register_parser(".csv")
def extract_text_csv(path: Path) -> str:
    """Извлечение текста из CSV (через csv.reader)."""
    lines: list[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            lines.append(",".join(row))
    return "\n".join(lines)


@register_parser(".xls")
def extract_text_xls(path: Path) -> str:
    """Извлечение текста из XLS (через xlrd)."""
    if xlrd is None:
        raise RuntimeError("xlrd не установлен")
    book = xlrd.open_workbook(path)
    lines: list[str] = []
    for sheet in book.sheets():
        for row_idx in range(sheet.nrows):
            row = sheet.row_values(row_idx)
            lines.append(",".join(str(cell) for cell in row))
    return "\n".join(lines)


@register_parser(".xlsx")
def extract_text_xlsx(path: Path) -> str:
    """Извлечение текста из XLSX (через openpyxl)."""
    if openpyxl is None:
        raise RuntimeError("openpyxl не установлен")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    lines: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            values = ["" if v is None else str(v) for v in row]
            lines.append(",".join(values))
    wb.close()
    return "\n".join(lines)


# ---------- Входная точка с поддержкой OCR ----------

def extract_text(file_path: Union[str, Path], language: str = "eng") -> str:
    """
    Извлечь текст из поддерживаемого файла.

    Поддерживаемые форматы:
      - Текстовые: .txt, .md, .pdf, .docx
      - Таблицы: .csv, .xls, .xlsx
      - Изображения (OCR): .jpg, .jpeg, .png, .tiff (через image_ocr.extract_text_image)

    :param file_path: путь к файлу.
    :param language: язык OCR (ISO-коды tesseract, напр. 'eng', 'rus', 'deu').
    :return: извлечённый текст.
    :raises ValueError: если расширение не поддерживается.
    :raises RuntimeError: если требуемая зависимость для формата не установлена.
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    logger.info("Extracting text from %s", path)

    # Ветвь для изображений — нужен отдельный параметр language
    if ext in {".jpg", ".jpeg", ".png", ".tiff"}:
        if extract_text_image is None:
            logger.error("OCR module unavailable for %s", path)
            raise RuntimeError("Модуль OCR недоступен: .image_ocr.extract_text_image не найден")
        text = extract_text_image(path, language=language)
        logger.debug("Extracted %d characters from %s via OCR", len(text), path)
        return text

    # Обычные «текстовые» форматы
    parser = _PARSER_REGISTRY.get(ext)
    if parser is None:
        logger.error("Unsupported/unknown file extension: %s", ext)
        raise ValueError(f"Unsupported/unknown file extension: {ext}")
    text = parser(path)
    logger.debug("Extracted %d characters from %s", len(text), path)
    return text


# ---------- Вспомогательные утилиты ----------

def merge_images_to_pdf(paths: list[Path]) -> Path:
    """Преобразовать несколько изображений в один PDF во временном файле.

    Обрабатываются изображения в различных цветовых пространствах и размерах.

    :param paths: список путей к изображениям.
    :return: путь к созданному временному PDF-файлу.
    """
    if not paths:
        raise ValueError("No images provided")

    images: list[Image.Image] = []
    max_w = max_h = 0
    for path in paths:
        with Image.open(path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.load()
            max_w = max(max_w, img.width)
            max_h = max(max_h, img.height)
            images.append(img)

    normalized = [
        ImageOps.pad(img, (max_w, max_h), color=(255, 255, 255))
        if img.size != (max_w, max_h)
        else img
        for img in images
    ]

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    first, *rest = normalized
    first.save(tmp.name, save_all=True, append_images=rest, format="PDF")
    tmp_path = Path(tmp.name)
    tmp.close()
    return tmp_path


__all__ = [
    "extract_text",
    "register_parser",
    "extract_text_txt",
    "extract_text_md",
    "extract_text_pdf",
    "extract_text_docx",
    "extract_text_csv",
    "extract_text_xls",
    "extract_text_xlsx",
    "merge_images_to_pdf",
    "parse_mrz",
    "translate_text",
]


try:  # Автообнаружение плагинов
    from plugins import load_plugins as _load_plugins

    _load_plugins()
except Exception:  # pragma: no cover - отсутствие плагинов не критично
    logger.debug("Plugin loading skipped", exc_info=True)


def translate_text(text: str, target_lang: str) -> str:
    """Перевести *text* на язык ``target_lang`` с помощью OpenRouter."""

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable required")

    model = OPENROUTER_MODEL or "openai/chatgpt-4o-mini"
    base_url = OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
    api_url = base_url.rstrip("/") + "/chat/completions"
    prompt = f"Translate the following text to {target_lang}:\n{text}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": OPENROUTER_SITE_URL or "https://github.com/docrouter",
        "X-Title": OPENROUTER_SITE_NAME or "DocRouter",
    }
    response = requests.post(api_url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return content.strip()
