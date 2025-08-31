from __future__ import annotations

import json
import logging
import mimetypes
import shutil
import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse, PlainTextResponse

from file_sorter import place_file
from models import Metadata, FileRecord
from .. import db as database, server
from .upload import UPLOAD_DIR
from .folders import _resolve_in_output

router = APIRouter()
logger = logging.getLogger(__name__)


def _scan_output_dir() -> None:
    """Просканировать выходную папку и добавить новые файлы в БД."""
    output_dir = Path(server.config.output_dir)
    if not output_dir.exists():
        return

    existing_paths = {Path(rec.path) for rec in database.list_files()}

    for file_path in output_dir.rglob("*"):
        if file_path.is_dir() or file_path.suffix == ".json":
            continue
        if file_path in existing_paths:
            continue

        metadata = Metadata()
        meta_file = file_path.with_suffix(file_path.suffix + ".json")
        if meta_file.exists():
            try:
                meta_dict = json.loads(meta_file.read_text(encoding="utf-8"))
                metadata = Metadata(**meta_dict)
            except Exception:  # pragma: no cover
                logger.warning("Failed to load metadata for %s", file_path)

        file_id = hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()
        database.add_file(file_id, file_path.name, metadata, str(file_path), "processed")
        existing_paths.add(file_path)


@router.get("/metadata/{file_id}", response_model=Metadata)
async def get_metadata(file_id: str):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return record.metadata


@router.get("/download/{file_id}")
async def download_file(file_id: str, lang: str | None = None):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if lang:
        extracted = record.metadata.extracted_text or ""
        orig_lang = record.metadata.language
        if lang == orig_lang:
            text = extracted
        elif record.translation_lang == lang and record.translated_text:
            text = record.translated_text
        else:
            text = await server.translate_text(extracted, lang)
            database.update_file(
                file_id,
                translated_text=text,
                translation_lang=lang,
            )
        headers = {
            "Content-Disposition": f"attachment; filename={record.filename}_{lang}.txt"
        }
        return PlainTextResponse(text, headers=headers)

    path = Path(record.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=path.name)


@router.get("/preview/{file_id}")
async def preview_file(file_id: str):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    content_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=content_type or "application/octet-stream")


@router.get("/files/{file_id}/details", response_model=FileRecord)
async def get_file_details(file_id: str, lang: str | None = None):
    record = database.get_details(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if lang:
        extracted = record.metadata.extracted_text or ""
        orig_lang = record.metadata.language
        if lang == orig_lang:
            text = extracted
        elif record.translation_lang == lang and record.translated_text:
            text = record.translated_text
        else:
            text = await server.translate_text(extracted, lang)
            database.update_file(
                file_id,
                translated_text=text,
                translation_lang=lang,
            )
            record.translated_text = text
            record.translation_lang = lang
        record.translated_text = record.translated_text or text
        record.translation_lang = lang
    return record


@router.get("/files", response_model=list[FileRecord])
async def list_files():
    _scan_output_dir()
    return database.list_files()



@router.patch("/files/{file_id}", response_model=FileRecord)
async def update_file(file_id: str, data: dict = Body(...)):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    metadata_updates = data.get("metadata") or {}
    new_metadata_dict = record.metadata.model_dump()
    if metadata_updates:
        new_metadata_dict.update(metadata_updates)
    new_metadata = Metadata(**new_metadata_dict)
    path_param = data.get("path")
    status = data.get("status")
    prompt = data.get("prompt")
    raw_response = data.get("raw_response")
    missing = data.get("missing")

    old_path = Path(record.path)
    if not old_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    dest_path = old_path
    confirmed = False

    if metadata_updates and not path_param:
        old_json = old_path.with_suffix(old_path.suffix + ".json")
        if old_json.exists():
            old_json.unlink()
        dest_path, _, confirmed = place_file(
            old_path,
            new_metadata_dict,
            server.config.output_dir,
            dry_run=False,
            needs_new_folder=True,
            confirm_callback=lambda _: True,
        )
        new_metadata = Metadata(**new_metadata_dict)
    elif path_param:
        old_json = old_path.with_suffix(old_path.suffix + ".json")
        if old_json.exists():
            old_json.unlink()
        dest_path = _resolve_in_output(path_param)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.exists():
            raise HTTPException(status_code=409, detail="Target already exists")
        shutil.move(str(old_path), dest_path)
        with open(dest_path.with_suffix(dest_path.suffix + ".json"), "w", encoding="utf-8") as f:
            json.dump(new_metadata_dict, f, ensure_ascii=False, indent=2)

    database.update_file(
        file_id,
        metadata=new_metadata if metadata_updates else None,
        path=str(dest_path) if (metadata_updates or path_param) else None,
        status=status,
        prompt=prompt,
        raw_response=raw_response,
        missing=missing,
        confirmed=confirmed if metadata_updates and not path_param else None,
        created_path=str(dest_path) if (metadata_updates and confirmed and not path_param) else None,
    )
    return database.get_file(file_id)


@router.post("/files/{file_id}/finalize", response_model=FileRecord)
async def finalize_file(file_id: str):
    """Завершить обработку «отложенного» файла.

    Перенести файл в целевую структуру (создавая недостающие каталоги) и
    обновить запись в БД.
    """
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if record.status != "pending":
        # Возвращаем текущую запись, ничего не делаем
        return record

    # Путь к временно загруженному файлу
    temp_path = record.path
    if not temp_path:
        temp_path = str(UPLOAD_DIR / f"{file_id}_{record.filename}")

    meta_dict = record.metadata.model_dump()
    dest_path, still_missing, confirmed = place_file(
        str(temp_path),
        meta_dict,
        server.config.output_dir,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _: True,
    )
    metadata = Metadata(**meta_dict)

    database.update_file(
        file_id,
        metadata,
        str(dest_path),
        "processed",
        record.prompt,
        record.raw_response,
        still_missing,
        suggested_path=str(dest_path),
        confirmed=confirmed,
        created_path=str(dest_path) if confirmed else None,
    )
    return database.get_file(file_id)
