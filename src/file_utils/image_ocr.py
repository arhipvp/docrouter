"""OCR utilities for image files."""

from pathlib import Path
from typing import Union

try:
    from PIL import Image
    import pytesseract
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise ModuleNotFoundError(
        "pytesseract and Pillow are required for OCR functionality"
    ) from exc


def extract_text_image(image_path: Union[str, Path], language: str = "eng") -> str:
    """Extract text from an image using Tesseract OCR.

    :param image_path: Path to the image file.
    :param language: Language for OCR (default 'eng').
    :return: Extracted text as a string.
    """
    img = Image.open(Path(image_path))
    return pytesseract.image_to_string(img, lang=language)
