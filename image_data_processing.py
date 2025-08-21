import logging
import time

from PIL import Image
import pytesseract

from data_processing_common import extract_file_metadata, sanitize_filename
from openrouter_client import fetch_metadata_from_llm
from error_handling import handle_model_error

logger = logging.getLogger(__name__)


def process_single_image(image_path: str, silent: bool = False, log_file: str | None = None):
    """OCR изображения → извлечение текста → метаданные файла + анализ через LLM."""
    start_time = time.time()

    try:
        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img)
    except Exception as e:
        handle_model_error(image_path, f"OCR error: {e}", response="", log_file=log_file)
        return None

    # Локальные метаданные файла
    file_meta = extract_file_metadata(image_path)

    # Анализ текста через LLM
    try:
        ai_meta = fetch_metadata_from_llm(text)
    except Exception as e:  # pragma: no cover - сетевые ошибки
        response = getattr(e, "response", "")
        handle_model_error(image_path, str(e), response, log_file=log_file)
        return None

    # Логирование времени обработки
    time_taken = time.time() - start_time
    summary = f"{image_path} ({time_taken:.2f}s)"
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    if not silent:
        logger.info(summary)

    return {
        "file_path": image_path,
        "text": text,
        "metadata": {
            "file": file_meta,
            "ai": ai_meta,
        },
    }


def process_image_files(image_paths: list[str], silent: bool = False, log_file: str | None = None):
    """Последовательно обработать список изображений."""
    results: list[dict] = []
    for path in image_paths:
        data = process_single_image(path, silent=silent, log_file=log_file)
        if data is not None:
            results.append(data)
    return results
