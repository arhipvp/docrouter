import os
import time
import logging
from PIL import Image
import pytesseract

from data_processing_common import sanitize_filename, extract_file_metadata
from error_handling import handle_model_error

logger = logging.getLogger(__name__)


def process_single_image(image_path: str, silent: bool = False, log_file: str | None = None):
    """Обработать одно изображение: OCR → базовые метаданные → простое имя и папка."""
    start_time = time.time()

    # 1) OCR
    try:
        with Image.open(image_path) as img:
            extracted_text = pytesseract.image_to_string(img)
    except Exception as e:
        handle_model_error(image_path, f"OCR error: {e}", response="", log_file=log_file)
        return None

    # 2) Метаданные файла
    metadata = extract_file_metadata(image_path)

    # 3) Генерация имени/папки (без LLM, минимально)
    try:
        foldername, filename, description = generate_image_metadata(image_path)
    except Exception as e:
        response = getattr(e, "response", "")
        handle_model_error(image_path, str(e), response, log_file=log_file)
        return None

    # 4) Лог
    time_taken = time.time() - start_time
    summary = f"{image_path} -> {foldername}/{filename} ({time_taken:.2f}s)"
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    if not silent:
        logger.info(summary)

    return {
        "file_path": image_path,
        "foldername": foldername,
        "filename": filename,
        "description": description,
        "text": extracted_text,
        "metadata": metadata,
    }


def process_image_files(image_paths: list[str], silent: bool = False, log_file: str | None = None):
    """Последовательно обработать список изображений."""
    results: list[dict] = []
    for image_path in image_paths:
        data = process_single_image(image_path, silent=silent, log_file=log_file)
        if data is not None:
            results.append(data)
    return results


def generate_image_metadata(image_path: str) -> tuple[str, str, str]:
    """Минимальная генерация: папка 'images', имя из базового названия файла, пустое описание."""
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    filename = sanitize_filename(base_name, max_words=3)
    foldername = "images"
    description = ""
    return foldername, filename, description
