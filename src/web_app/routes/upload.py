from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from file_utils.embeddings import get_embedding
from file_sorter import place_file, get_folder_tree
from models import Metadata, UploadResponse
from metadata_generation import OpenRouterError
from .. import db as database, server

router = APIRouter()

logger = logging.getLogger(__name__)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    dry_run: bool = False,
):
    """Загрузить файл и обработать его."""
    file_id = str(uuid.uuid4())
    temp_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as dest:
            dest.write(contents)

        # Извлечение текста + генерация метаданных
        lang = language or server.config.tesseract_lang
        text = server.extract_text(temp_path, language=lang)
        folder_tree = get_folder_tree(server.config.output_dir)
        try:
            meta_result = await server.metadata_generation.generate_metadata(
                text, folder_tree=folder_tree
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
        metadata.language = lang
        embedding = await get_embedding(text)

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
    except Exception as exc:  # pragma: no cover
        logger.exception("Upload/processing failed for %s", file.filename)
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
            embedding=embedding,
            suggested_path=str(dest_path),
            confirmed=confirmed,
            created_path=str(dest_path) if confirmed else None,
        )
        return UploadResponse(
            id=file_id,
            status="pending",
            missing=missing,
            suggested_path=str(dest_path),
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
        embedding=embedding,
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
        lang = language or server.config.tesseract_lang
        text = server.extract_text(pdf_path, language=lang)
        folder_tree = get_folder_tree(server.config.output_dir)
        try:
            meta_result = await server.metadata_generation.generate_metadata(
                text, folder_tree=folder_tree
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
        metadata.language = lang
        embedding = await get_embedding(text)

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
            embedding=embedding,
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
        embedding=embedding,
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
