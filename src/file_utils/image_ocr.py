"""OCR utilities for image files."""

from pathlib import Path
from typing import Union
import logging

try:
    from PIL import Image
    import pytesseract
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise ModuleNotFoundError(
        "pytesseract and Pillow are required for OCR functionality"
    ) from exc


logger = logging.getLogger(__name__)


def extract_text_image(image_path: Union[str, Path], language: str = "eng") -> str:
    """Extract text from an image using Tesseract OCR.

    :param image_path: Path to the image file.
    :param language: Language for OCR (default 'eng').
    :return: Extracted text as a string.
    """
    try:
        with Image.open(Path(image_path)) as img:
            return pytesseract.image_to_string(img, lang=language)
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR executable not found. Please install Tesseract and ensure it's in PATH."
        ) from exc
    except pytesseract.TesseractError as exc:
        if language != "eng":
            logger.warning(
                "Tesseract language '%s' unavailable, falling back to 'eng'", language
            )
            try:
                with Image.open(Path(image_path)) as img:
                    return pytesseract.image_to_string(img, lang="eng")
            except pytesseract.TesseractError:
                pass
        raise exc
