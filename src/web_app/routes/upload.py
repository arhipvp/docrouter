from __future__ import annotations

import logging
import mimetypes
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from file_sorter import place_file, get_folder_tree, sanitize_filename
from file_utils import UnsupportedFileType
from models import Metadata, UploadResponse
from services.openrouter import OpenRouterError
from .. import db as database
from ..db import run_db
from config import config

router = APIRouter()

logger = logging.getLogger(__name__)
# Allow overriding the upload directory via the ``UPLOAD_DIR`` environment
# variable. If creating the directory fails due to insufficient permissions,
# fall back to a temporary location to keep the application functional.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Сопоставление пользовательских кодов языков с кодами tesseract
LANG_MAP = {"en": "eng", "ru": "rus", "de": "deu"}
REV_LANG_MAP = {v: k for k, v in LANG_MAP.items()}


def _check_tesseract() -> bool:
    """Проверить доступность бинарника tesseract."""
    if config.tesseract_cmd:
        cmd_path = Path(config.tesseract_cmd)
        if cmd_path.exists():
            logger.info("Используем указанный путь к tesseract: %s", cmd_path)
            return True
        logger.warning(
            "Указанный путь к tesseract не найден: %s", config.tesseract_cmd
        )
    system_cmd = shutil.which("tesseract")
    if system_cmd:
        logger.info("Найден tesseract в PATH: %s", system_cmd)
        return True
    logger.warning("Бинарник tesseract не найден. OCR будет недоступен")
    return False

# Вычисляем доступность OCR при загрузке модуля
OCR_AVAILABLE = _check_tesseract()


async def process_uploaded(
    path: Path, language: str | None, dry_run: bool
) -> tuple[Metadata, Path, list[str], dict]:
    """Обработать загруженный файл и вернуть метаданные."""
    from .. import server

    lang_display = language or REV_LANG_MAP.get(
        server.config.tesseract_lang, server.config.tesseract_lang
    )
    lang_ocr = LANG_MAP.get(lang_display, lang_display)
    try:
        text = server.extract_text(path, language=lang_ocr)
        folder_tree, folder_index = get_folder_tree(server.config.output_dir)
        meta_result = await server.metadata_generation.generate_metadata(
            text, folder_tree=folder_tree, folder_index=folder_index
        )
        raw_meta = meta_result["metadata"]
        metadata = Metadata(**raw_meta) if isinstance(raw_meta, dict) else raw_meta
        metadata.extracted_text = text
        metadata.language = lang_display
        meta_dict = metadata.model_dump()
        meta_dict["summary"] = metadata.summary
        dest_path, missing, _ = place_file(
            str(path),
            meta_dict,
            server.config.output_dir,
            dry_run=dry_run,
            needs_new_folder=metadata.needs_new_folder,
            confirm_callback=lambda _paths: False,
        )
        metadata = Metadata(**meta_dict)
    except OpenRouterError as exc:
        logger.exception("Metadata generation failed for %s", path.name)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except UnsupportedFileType as exc:
        logger.exception("Upload/processing failed for %s", path.name)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Upload/processing failed for %s", path.name)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Upload/processing failed for %s", path.name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return metadata, dest_path, missing, meta_result


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    dry_run: bool = False,
):
    """Загрузить файл и обработать его."""
    from .. import server
    if not OCR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="OCR недоступен: бинарник tesseract не найден",
        )
    file_id = str(uuid.uuid4())
    filename = file.filename or ""
    filename = sanitize_filename(Path(filename).name)
    if not filename:
        guessed_ext = mimetypes.guess_extension(file.content_type or "") or ""
        filename = sanitize_filename(f"upload{guessed_ext}")
    temp_path = UPLOAD_DIR / f"{file_id}_{filename}"
    with open(temp_path, "wb") as dest:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            dest.write(chunk)

    metadata, dest_path, missing, meta_result = await process_uploaded(
        temp_path, language, dry_run
    )
    final_path = dest_path if not dry_run and not missing else temp_path
    sources = [file.filename]

    await run_db(
        database.add_file,
        file_id,
        file.filename,
        metadata,
        str(final_path),
        "review",
        meta_result.get("prompt"),
        meta_result.get("raw_response"),
        missing,
        sources=sources,
        suggested_path=str(dest_path),
    )

    return UploadResponse(
        id=file_id,
        filename=file.filename,
        metadata=metadata,
        tags_ru=metadata.tags_ru,
        tags_en=metadata.tags_en,
        path=str(final_path),
        status="review",
        missing=missing,
        sources=sources,
        prompt=meta_result.get("prompt"),
        raw_response=meta_result.get("raw_response"),
        suggested_path=str(dest_path),
    )


@router.post("/upload/images", response_model=UploadResponse)
async def upload_images(
    files: list[UploadFile] = File(...),
    language: str | None = Form(None),
    dry_run: bool = False,
):
    """Загрузить несколько изображений, объединить их и обработать как PDF."""
    from .. import server
    if not OCR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="OCR недоступен: бинарник tesseract не найден",
        )
    file_id = str(uuid.uuid4())
    temp_dir = UPLOAD_DIR / file_id
    temp_dir.mkdir(exist_ok=True)

    sorted_files = sorted(files, key=lambda f: f.filename or "")
    image_paths: list[Path] = []
    for idx, img in enumerate(sorted_files):
        temp_img = temp_dir / f"{idx:03d}_{img.filename}"
        with open(temp_img, "wb") as dest:
            while True:
                chunk = await img.read(1024 * 1024)
                if not chunk:
                    break
                dest.write(chunk)
        image_paths.append(temp_img)

    try:
        tmp_pdf = server.merge_images_to_pdf(image_paths)
        pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
        shutil.move(tmp_pdf, pdf_path)
    except Exception as exc:  # pragma: no cover
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.exception("Failed to merge images: %s", [f.filename for f in files])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    shutil.rmtree(temp_dir, ignore_errors=True)

    metadata, dest_path, missing, meta_result = await process_uploaded(
        pdf_path, language, dry_run
    )
    final_path = dest_path if not dry_run and not missing else pdf_path
    sources = [f.filename for f in sorted_files]

    await run_db(
        database.add_file,
        file_id,
        pdf_path.name,
        metadata,
        str(final_path),
        "review",
        meta_result.get("prompt"),
        meta_result.get("raw_response"),
        missing,
        sources=sources,
        suggested_path=str(dest_path),
    )

    return UploadResponse(
        id=file_id,
        filename=pdf_path.name,
        metadata=metadata,
        tags_ru=metadata.tags_ru,
        tags_en=metadata.tags_en,
        path=str(final_path),
        status="review",
        missing=missing,
        sources=sources,
        prompt=meta_result.get("prompt"),
        raw_response=meta_result.get("raw_response"),
        suggested_path=str(dest_path),
    )
