from __future__ import annotations

import logging
import mimetypes
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from file_sorter import place_file, get_folder_tree
from file_utils import UnsupportedFileType
from models import Metadata, UploadResponse
from services.openrouter import OpenRouterError
from .. import db as database, server

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


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    dry_run: bool = False,
):
    """Загрузить файл и обработать его."""
    file_id = str(uuid.uuid4())
    filename = file.filename or ""
    if not filename:
        guessed_ext = mimetypes.guess_extension(file.content_type or "") or ""
        filename = f"upload{guessed_ext}"
    temp_path = UPLOAD_DIR / f"{file_id}_{filename}"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as dest:
            dest.write(contents)

        # Извлечение текста + генерация метаданных
        lang_display = language or REV_LANG_MAP.get(
            server.config.tesseract_lang, server.config.tesseract_lang
        )
        lang_ocr = LANG_MAP.get(lang_display, lang_display)
        text = server.extract_text(temp_path, language=lang_ocr)
        folder_tree, folder_index = get_folder_tree(server.config.output_dir)
        try:
            meta_result = await server.metadata_generation.generate_metadata(
                text, folder_tree=folder_tree, folder_index=folder_index
            )
        except OpenRouterError as exc:
            logger.exception("Metadata generation failed for %s", file.filename)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        raw_meta = meta_result["metadata"]
        if isinstance(raw_meta, dict):
            metadata = Metadata(**raw_meta)
        else:
            metadata = raw_meta
        metadata.extracted_text = text
        metadata.language = lang_display

        meta_dict = metadata.model_dump()
        # Раскладываем файл по директориям без создания недостающих
        dest_path, missing, confirmed = place_file(
            str(temp_path),
            meta_dict,
            server.config.output_dir,
            dry_run=dry_run,
            needs_new_folder=metadata.needs_new_folder,
        )
        metadata = Metadata(**meta_dict)

    except HTTPException:
        raise
    except UnsupportedFileType as exc:
        logger.exception("Upload/processing failed for %s", filename)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        logger.exception("Upload/processing failed for %s", filename)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Upload/processing failed for %s", filename)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if missing:
        database.add_file(
            file_id,
            file.filename,
            metadata,
            str(temp_path),
            "pending",
            meta_result.get("prompt"),
            meta_result.get("raw_response"),
            missing,
            suggested_path=str(dest_path),
            confirmed=confirmed,
            created_path=str(dest_path) if confirmed else None,
        )
        return UploadResponse(
            id=file_id,
            status="pending",
            missing=missing,
            suggested_path=str(dest_path),
            prompt=meta_result.get("prompt"),
            raw_response=meta_result.get("raw_response"),
        )

    status = "dry_run" if dry_run else "processed"

    # Сохраняем запись в БД
    database.add_file(
        file_id,
        file.filename,
        metadata,
        str(dest_path),
        status,
        meta_result.get("prompt"),
        meta_result.get("raw_response"),
        [],  # missing
        suggested_path=str(dest_path),
        confirmed=confirmed,
        created_path=str(dest_path) if confirmed else None,
    )

    return UploadResponse(
        id=file_id,
        filename=file.filename,
        metadata=metadata,
        tags_ru=metadata.tags_ru,
        tags_en=metadata.tags_en,
        path=str(dest_path),
        status=status,
        missing=[],
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
    file_id = str(uuid.uuid4())
    temp_dir = UPLOAD_DIR / file_id
    temp_dir.mkdir(exist_ok=True)

    sorted_files = sorted(files, key=lambda f: f.filename or "")
    image_paths: list[Path] = []
    for idx, img in enumerate(sorted_files):
        temp_img = temp_dir / f"{idx:03d}_{img.filename}"
        contents = await img.read()
        with open(temp_img, "wb") as dest:
            dest.write(contents)
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

    try:
        lang_display = language or REV_LANG_MAP.get(
            server.config.tesseract_lang, server.config.tesseract_lang
        )
        lang_ocr = LANG_MAP.get(lang_display, lang_display)
        text = server.extract_text(pdf_path, language=lang_ocr)
        folder_tree, folder_index = get_folder_tree(server.config.output_dir)
        try:
            meta_result = await server.metadata_generation.generate_metadata(
                text, folder_tree=folder_tree, folder_index=folder_index
            )
        except OpenRouterError as exc:
            logger.exception("Metadata generation failed for images")
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        raw_meta = meta_result["metadata"]
        if isinstance(raw_meta, dict):
            metadata = Metadata(**raw_meta)
        else:
            metadata = raw_meta
        metadata.extracted_text = text
        metadata.language = lang_display

        meta_dict = metadata.model_dump()
        dest_path, missing, confirmed = place_file(
            str(pdf_path),
            meta_dict,
            server.config.output_dir,
            dry_run=dry_run,
            needs_new_folder=metadata.needs_new_folder,
        )
        metadata = Metadata(**meta_dict)
    except HTTPException:
        raise
    except UnsupportedFileType as exc:
        logger.exception("Upload/processing failed for images")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Upload/processing failed for images")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    sources = [f.filename for f in sorted_files]

    if missing:
        database.add_file(
            file_id,
            pdf_path.name,
            metadata,
            str(pdf_path),
            "pending",
            meta_result.get("prompt"),
            meta_result.get("raw_response"),
            missing,
            sources=sources,
            suggested_path=str(dest_path),
            confirmed=confirmed,
            created_path=str(dest_path) if confirmed else None,
        )
        return UploadResponse(
            id=file_id,
            status="pending",
            missing=missing,
            sources=sources,
            suggested_path=str(dest_path),
            prompt=meta_result.get("prompt"),
            raw_response=meta_result.get("raw_response"),
        )

    status = "dry_run" if dry_run else "processed"
    database.add_file(
        file_id,
        pdf_path.name,
        metadata,
        str(dest_path),
        status,
        meta_result.get("prompt"),
        meta_result.get("raw_response"),
        [],
        sources=sources,
        suggested_path=str(dest_path),
        confirmed=confirmed,
        created_path=str(dest_path) if confirmed else None,
    )

    return UploadResponse(
        id=file_id,
        filename=pdf_path.name,
        metadata=metadata,
        tags_ru=metadata.tags_ru,
        tags_en=metadata.tags_en,
        path=str(dest_path),
        status=status,
        missing=[],
        sources=sources,
        prompt=meta_result.get("prompt"),
        raw_response=meta_result.get("raw_response"),
        suggested_path=str(dest_path),
    )
