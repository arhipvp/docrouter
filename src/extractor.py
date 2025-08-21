from pathlib import Path

from PIL import Image
import pytesseract


def extract_text(path: Path) -> str:
    """Извлечь текст из изображения или PDF-файла."""
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}:
        image = Image.open(path)
        return pytesseract.image_to_string(image)
    elif suffix == ".pdf":
        try:
            from pdfminer.high_level import extract_text as pdf_extract_text
        except Exception as exc:
            raise RuntimeError("Для обработки PDF требуется пакет pdfminer.six") from exc
        return pdf_extract_text(str(path))
    else:
        raise ValueError(f"Неподдерживаемый тип файла: {suffix}")
