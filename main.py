import os
import json
import argparse
import logging
import shutil
import time
from typing import Dict, Any

from PIL import Image
import pytesseract

from file_utils import collect_file_paths, read_file_data
from data_processing_common import build_storage_path, write_metadata
from openrouter_client import fetch_metadata_from_llm
from error_handling import handle_model_error


def extract_text_and_metadata(file_path: str) -> tuple[str, Dict[str, Any]]:
    """Извлечь текст (OCR для изображений) и базовые метаданные файла."""
    metadata: Dict[str, Any] = {
        "original_name": os.path.basename(file_path),
        "size": os.path.getsize(file_path),
        "created": time.ctime(os.path.getctime(file_path)),
    }
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"}:
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
        except Exception as ocr_err:
            metadata["ocr_error"] = str(ocr_err)
    else:
        data = read_file_data(file_path)
        if data:
            text = data
    return text, metadata


def process_file(file_path: str, output_path: str, dry_run: bool, logger: logging.Logger) -> None:
    """Обработать один файл: извлечение текста → LLM → перемещение и сохранение .json."""
    text, metadata = extract_text_and_metadata(file_path)

    try:
        llm_info = fetch_metadata_from_llm(text)
    except Exception as e:
        logger.error("LLM failed for %s: %s", file_path, e)
        handle_model_error(
            file_path,
            f"LLM error: {e}",
            getattr(e, "response", ""),
            unsorted_dir=os.path.join(output_path, "Unsorted"),
        )
        return

    # Построить путь назначения (общая утилита)
    destination = build_storage_path(llm_info, file_path, base_path=output_path)

    if dry_run:
        logger.info("Dry-run: would move %s -> %s", file_path, destination)
        # Записать метаданные в режиме dry-run (утилита сама решит, как логировать/писать)
        write_metadata(destination, llm_info, metadata, dry_run=True, logger=logger)
        return

    try:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.move(file_path, destination)
        logger.info("Moved %s -> %s", file_path, destination)

        # Сохранить метаданные рядом с файлом (через общую утилиту)
        write_metadata(destination, llm_info, metadata, dry_run=False, logger=logger)
    except Exception as e:
        logger.error("Failed to move %s: %s", file_path, e)
        handle_model_error(
            file_path,
            f"File move error: {e}",
            "",
            unsorted_dir=os.path.join(output_path, "Unsorted"),
        )


def process_input_folder(input_path: str, output_path: str, dry_run: bool, logger: logging.Logger) -> None:
    """Обойти входную директорию и обработать все файлы."""
    for path in collect_file_paths(input_path):
        try:
            process_file(path, output_path, dry_run, logger)
        except Exception as e:
            logger.error("Unhandled error for %s: %s", path, e)


def setup_logger(log_file: str | None) -> logging.Logger:
    """Инициализировать логгер консоль + файл (опционально)."""
    logger = logging.getLogger("docrouter")
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(file_handler)

    return logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Process documents in a folder.")
    parser.add_argument("input", help="Path to input folder with documents")
    parser.add_argument("--output", default="Archive", help="Base output folder")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without moving files")
    parser.add_argument("--log-file", default="docrouter.log", help="Path to log file")
    args = parser.parse_args()

    logger = setup_logger(args.log_file)
    logger.info("Starting processing: input=%s output=%s dry_run=%s", args.input, args.output, args.dry_run)

    process_input_folder(args.input, args.output, args.dry_run, logger)


if __name__ == "__main__":
    main()
