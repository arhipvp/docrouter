"""Utility functions for extracting text from files."""

from pathlib import Path
from typing import Union

from .image_ocr import extract_text_image


def extract_text(file_path: Union[str, Path], language: str = "eng") -> str:
    """Extract text from a supported file.

    Currently supports plain text files and images (.jpg, .jpeg).

    :param file_path: Path to the file.
    :param language: Language for OCR when processing images.
    :return: Extracted text.
    :raises ValueError: If the file format is not supported.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".jpg", ".jpeg"}:
        return extract_text_image(path, language=language)
    elif suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
