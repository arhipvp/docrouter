from __future__ import annotations

import json
import logging
import mimetypes
import shutil
import hashlib
import time
from pathlib import Path
import httpx

try:
    import ocr_pipeline
except Exception:  # pragma: no cover - optional dependency
    ocr_pipeline = None  # type: ignore

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse, PlainTextResponse

from file_sorter import place_file
from models import Metadata, FileRecord
from .. import db as database, server
from ..db import run_db
from .upload import UPLOAD_DIR
from .folders import _resolve_in_output
from services.openrouter import OpenRouterError

router = APIRouter()
logger = logging.getLogger(__name__)

SCAN_CACHE_TTL = 5.0  # seconds
_last_scan_time = 0.0
_last_upload_mtime = 0.0


def _latest_upload_mtime() -> float:
    """Вернуть максимальное время изменения в каталоге загрузок."""
    if not UPLOAD_DIR.exists():
        return 0.0
    mtimes = [UPLOAD_DIR.stat().st_mtime]
    for path in UPLOAD_DIR.rglob("*"):
        try:
            mtimes.append(path.stat().st_mtime)
        except FileNotFoundError:
            continue
        except PermissionError:
            continue
    return max(mtimes)


def _should_rescan() -> bool:
    """Нужно ли повторно сканировать выходной каталог."""
    global _last_scan_time, _last_upload_mtime
    now = time.time()
    latest_upload = _latest_upload_mtime()
    if (now - _last_scan_time > SCAN_CACHE_TTL) or (latest_upload > _last_upload_mtime):
        _last_scan_time = now
        _last_upload_mtime = latest_upload
        return True
    return False


async def _scan_output_dir() -> None:
    """Просканировать выходную папку и добавить новые файлы в БД."""
    output_dir = Path(server.config.output_dir)
    if not output_dir.exists():
        return

    records = await run_db(database.list_files)
    existing_records = {Path(rec.path): rec.id for rec in records}
    existing_paths = set(existing_records)

    for file_path in output_dir.rglob("*"):
        if file_path.is_dir():
            continue

        if file_path.suffix == ".json":
            doc_path = file_path.with_suffix("")
            if not doc_path.exists():
                if doc_path in existing_paths:
                    continue
                metadata = Metadata()
                try:
                    meta_dict = json.loads(file_path.read_text(encoding="utf-8"))
                    metadata = Metadata(**meta_dict)
                except Exception:  # pragma: no cover
                    logger.warning("Failed to load metadata for %s", file_path)

                file_id = hashlib.sha1(str(doc_path).encode("utf-8")).hexdigest()
                await run_db(
                    database.add_file,
                    file_id,
                    doc_path.name,
                    metadata,
                    str(doc_path),
                    "missing",
                )
                existing_records[doc_path] = file_id
                existing_paths.add(doc_path)
            continue

        meta_file = file_path.with_suffix(file_path.suffix + ".json")

        if file_path in existing_paths:
            file_id = existing_records[file_path]
            if meta_file.exists() and meta_file.stat().st_mtime > file_path.stat().st_mtime:
                try:
                    meta_dict = json.loads(meta_file.read_text(encoding="utf-8"))
                    metadata = Metadata(**meta_dict)
                    await run_db(database.update_file, file_id, metadata=metadata)
                except Exception:  # pragma: no cover
                    logger.warning("Failed to load metadata for %s", file_path)
            continue

        metadata = Metadata()
        if meta_file.exists():
            try:
                meta_dict = json.loads(meta_file.read_text(encoding="utf-8"))
                metadata = Metadata(**meta_dict)
            except Exception:  # pragma: no cover
                logger.warning("Failed to load metadata for %s", file_path)

        file_id = hashlib.sha1(file_path.read_bytes()).hexdigest()
        await run_db(
            database.add_file,
            file_id,
            file_path.name,
            metadata,
            str(file_path),
            "processed",
        )
        existing_records[file_path] = file_id
        existing_paths.add(file_path)

    for rec in await run_db(database.list_files):
        path = Path(rec.path)
        if rec.status != "missing" and not path.exists():
            await run_db(database.delete_file, rec.id)


@router.get("/metadata/{file_id}", response_model=Metadata)
async def get_metadata(file_id: str):
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return record.metadata


@router.get("/download/{file_id}")
async def download_file(file_id: str, lang: str | None = None):
    record = await run_db(database.get_file, file_id)
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
            try:
                text = await server.translate_text(extracted, lang)
            except (httpx.HTTPError, RuntimeError) as e:
                raise HTTPException(
                    status_code=502,
                    detail="Translation service unavailable",
                ) from e
            await run_db(
                database.update_file,
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
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    content_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=content_type or "application/octet-stream")


@router.get("/files/{file_id}/details", response_model=FileRecord)
async def get_file_details(file_id: str, lang: str | None = None):
    record = await run_db(database.get_details, file_id)
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
            try:
                text = await server.translate_text(extracted, lang)
            except (httpx.HTTPError, RuntimeError) as e:
                raise HTTPException(
                    status_code=502,
                    detail="Translation service unavailable",
                ) from e
            await run_db(
                database.update_file,
                file_id,
                translated_text=text,
                translation_lang=lang,
            )
            record.translated_text = text
            record.translation_lang = lang
        record.translated_text = record.translated_text or text
        record.translation_lang = lang
    record.sources = None
    return record


@router.get("/files/{file_id}/text", response_class=PlainTextResponse)
async def get_file_text(file_id: str):
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return record.metadata.extracted_text or ""


@router.get("/files", response_model=list[FileRecord])
async def list_files(force: bool = False):
    global _last_scan_time, _last_upload_mtime
    if force:
        await _scan_output_dir()
        _last_scan_time = time.time()
        _last_upload_mtime = _latest_upload_mtime()
    elif _should_rescan():
        await _scan_output_dir()
    return await run_db(database.list_files)


@router.get("/files/search", response_model=list[FileRecord])
async def search_files_route(q: str):
    return await run_db(database.search_files, q)



@router.patch("/files/{file_id}", response_model=FileRecord)
async def update_file(file_id: str, data: dict = Body(...)):
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    metadata_updates = data.get("metadata") or {}
    allowed_fields = set(Metadata.model_fields.keys())
    metadata_updates = {k: v for k, v in metadata_updates.items() if k in allowed_fields}
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

    await run_db(
        database.update_file,
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
    return await run_db(database.get_file, file_id)


@router.post("/files/{file_id}/finalize", response_model=FileRecord)
async def finalize_file(file_id: str, data: dict = Body(...)):
    """Завершить обработку файла и при необходимости создать каталоги."""
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if record.status not in {"pending", "review"}:
        return record

    missing = data.get("missing") or []
    confirm = bool(data.get("confirm"))

    if not confirm:
        await run_db(database.update_file, file_id, missing=missing)
        return await run_db(database.get_file, file_id)

    temp_path = record.path or str(UPLOAD_DIR / f"{file_id}_{record.filename}")

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

    await run_db(
        database.update_file,
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
    return await run_db(database.get_file, file_id)


@router.get("/files/{file_id}/review")
async def review_file(file_id: str):
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "suggested_path": record.suggested_path,
        "missing": record.missing,
        "metadata": record.metadata,
    }


@router.post("/files/{file_id}/rerun_ocr")
async def rerun_ocr(file_id: str, language: str = Body(...), psm: int = Body(3)):
    record = await run_db(database.get_file, file_id)
    if not record or not record.path:
        raise HTTPException(status_code=404, detail="File not found")
    extract = getattr(ocr_pipeline, "extract_text", None)
    if extract is None:
        raise HTTPException(status_code=500, detail="OCR pipeline not available")
    try:
        text = extract(record.path, language=language, psm=psm)
    except Exception as exc:  # pragma: no cover - depends on OCR setup
        logger.exception("OCR rerun failed for %s", file_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    metadata = record.metadata
    metadata.extracted_text = text
    metadata.language = language
    await run_db(database.update_file, file_id, metadata=metadata, status="review")
    return {"extracted_text": text}


@router.post("/files/{file_id}/regenerate", response_model=FileRecord)
async def regenerate_file(file_id: str, message: str | None = Body(None, embed=True)):
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    text = record.metadata.extracted_text or ""
    if message:
        text += "\n" + message

    try:
        meta_result = await server.metadata_generation.generate_metadata(text)
    except OpenRouterError as exc:
        logger.exception("Metadata regeneration failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - сеть может быть недоступна
        logger.exception("Metadata regeneration failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raw_meta = meta_result.get("metadata")
    new_meta = raw_meta if isinstance(raw_meta, Metadata) else Metadata(**raw_meta)
    # Сохраняем уже известные поля, если модель ничего не вернула
    base_meta = record.metadata.model_dump()
    base_meta.update(
        {k: v for k, v in new_meta.model_dump(exclude_unset=True).items() if v is not None}
    )
    metadata = Metadata(**base_meta)
    metadata.extracted_text = record.metadata.extracted_text
    metadata.language = record.metadata.language
    meta_dict = metadata.model_dump()
    dest_path_tmp, missing, _ = place_file(
        record.path,
        meta_dict,
        server.config.output_dir,
        dry_run=True,
        needs_new_folder=metadata.needs_new_folder,
        confirm_callback=lambda _paths: False,
    )
    metadata = Metadata(**meta_dict)
    orig_path = Path(record.path)
    if dest_path_tmp.parent == orig_path.parent and dest_path_tmp.stem.startswith(
        orig_path.stem + "_"
    ):
        dest_path = orig_path
        metadata.new_name_translit = record.metadata.new_name_translit
    else:
        dest_path = dest_path_tmp

    await run_db(
        database.update_file,
        file_id,
        metadata=metadata,
        prompt=meta_result.get("prompt"),
        raw_response=meta_result.get("raw_response"),
        missing=missing,
        suggested_path=str(dest_path),
    )
    return await run_db(database.get_file, file_id)


@router.post("/files/{file_id}/comment", response_model=FileRecord)
async def comment_file(file_id: str, message: str = Body(..., embed=True)):
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    await run_db(database.add_chat_message, file_id, "user", message)

    text = (record.metadata.extracted_text or "") + "\n" + message
    try:
        meta_result = await server.metadata_generation.generate_metadata(text)
    except OpenRouterError as exc:
        logger.exception("Metadata regeneration failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - сеть может быть недоступна
        logger.exception("Metadata regeneration failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raw_meta = meta_result.get("metadata")
    new_meta = raw_meta if isinstance(raw_meta, Metadata) else Metadata(**raw_meta)
    base_meta = record.metadata.model_dump()
    base_meta.update(
        {k: v for k, v in new_meta.model_dump(exclude_unset=True).items() if v is not None}
    )
    metadata = Metadata(**base_meta)
    metadata.extracted_text = record.metadata.extracted_text
    metadata.language = record.metadata.language

    meta_dict = metadata.model_dump()
    dest_path_tmp, missing, _ = place_file(
        record.path,
        meta_dict,
        server.config.output_dir,
        dry_run=True,
        needs_new_folder=metadata.needs_new_folder,
        confirm_callback=lambda _paths: False,
    )
    metadata = Metadata(**meta_dict)
    orig_path = Path(record.path)
    if dest_path_tmp.parent == orig_path.parent and dest_path_tmp.stem.startswith(
        orig_path.stem + "_"
    ):
        dest_path = orig_path
        metadata.new_name_translit = record.metadata.new_name_translit
    else:
        dest_path = dest_path_tmp

    await run_db(
        database.update_file,
        file_id,
        metadata=metadata,
        prompt=meta_result.get("prompt"),
        raw_response=meta_result.get("raw_response"),
        missing=missing,
        suggested_path=str(dest_path),
        review_comment=message,
    )
    return await run_db(database.get_file, file_id)
