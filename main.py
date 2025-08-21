import os
import json
import argparse
import logging
import shutil
import time
from typing import Dict, Any

from PIL import Image
import pytesseract
from openrouter_client import fetch_metadata_from_llm

from file_utils import collect_file_paths, read_file_data
from data_processing_common import sanitize_filename


def extract_text_and_metadata(file_path: str) -> tuple[str, Dict[str, Any]]:
    """Extract text (using OCR if needed) and gather basic file metadata."""
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


def build_storage_path(base_path: str, info: Dict[str, Any], original_path: str) -> str:
    """Build destination path based on LLM info."""
    category = info.get("category") or "Unsorted"
    subcategory = info.get("subcategory") or "General"
    org = info.get("person") or info.get("issuer") or "Unknown"
    filename = info.get("suggested_filename") or os.path.splitext(os.path.basename(original_path))[0]
    filename = sanitize_filename(filename)
    date_part = info.get("date")
    if date_part:
        filename = f"{date_part}__{filename}"
    ext = os.path.splitext(original_path)[1]
    dest_dir = os.path.join(base_path, category, subcategory, org)
    dest_file = os.path.join(dest_dir, f"{filename}{ext}")
    return dest_file


def process_file(file_path: str, output_path: str, dry_run: bool, logger: logging.Logger) -> None:
    text, metadata = extract_text_and_metadata(file_path)
    try:
        llm_info = fetch_metadata_from_llm(text)
    except Exception as e:
        logger.error("LLM failed for %s: %s", file_path, e)
        unsorted_dir = os.path.join(output_path, "Unsorted")
        dest = os.path.join(unsorted_dir, os.path.basename(file_path))
        if dry_run:
            logger.info("Dry-run: would move %s -> %s", file_path, dest)
            return
        os.makedirs(unsorted_dir, exist_ok=True)
        shutil.move(file_path, dest)
        logger.info("Moved %s -> %s", file_path, dest)
        return
    destination = build_storage_path(output_path, llm_info, file_path)
    if dry_run:
        logger.info("Dry-run: would move %s -> %s", file_path, destination)
        return
    try:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.move(file_path, destination)
        logger.info("Moved %s -> %s", file_path, destination)
        meta_path = destination + ".json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"llm": llm_info, "file": metadata}, f, ensure_ascii=False, indent=2)
        logger.info("Wrote metadata %s", meta_path)
    except Exception as e:
        logger.error("Failed to move %s: %s", file_path, e)
        unsorted_dir = os.path.join(output_path, "Unsorted")
        os.makedirs(unsorted_dir, exist_ok=True)
        shutil.move(file_path, os.path.join(unsorted_dir, os.path.basename(file_path)))


def process_input_folder(input_path: str, output_path: str, dry_run: bool, logger: logging.Logger) -> None:
    for path in collect_file_paths(input_path):
        try:
            process_file(path, output_path, dry_run, logger)
        except Exception as e:
            logger.error("Unhandled error for %s: %s", path, e)


def setup_logger(log_file: str | None) -> logging.Logger:
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
