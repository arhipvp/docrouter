from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
import json
import mimetypes


from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, Body
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
try:
    from fastapi.templating import Jinja2Templates
except Exception:  # pragma: no cover
    Jinja2Templates = None  # type: ignore[misc,assignment]

from config import load_config
from logging_config import setup_logging
from file_utils import extract_text, merge_images_to_pdf
from file_utils.embeddings import get_embedding, cosine_similarity
from file_sorter import place_file, get_folder_tree
import metadata_generation
from . import database

app = FastAPI()

# --------- Статика и шаблоны ----------
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:  # pragma: no cover
    logging.getLogger(__name__).warning(
        "Static directory %s does not exist; static files will not be served.",
        STATIC_DIR,
    )
if Jinja2Templates:
    try:
        templates = Jinja2Templates(directory=TEMPLATES_DIR)
    except AssertionError:  # pragma: no cover
        templates = None
else:
    templates = None


@app.get("/")
async def serve_index(request: Request):
    """Отдать форму загрузки."""
    if templates is not None:
        return templates.TemplateResponse("index.html", {"request": request})
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():  # страховка
        return HTMLResponse("<h1>Docrouter</h1><p>templates/index.html не найден</p>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# --------- Конфиг и логирование ----------
config = load_config()
try:
    setup_logging(config.log_level, None)  # type: ignore[arg-type]
except Exception:
    logging.basicConfig(level=getattr(logging, str(config.log_level).upper(), logging.INFO))

logger = logging.getLogger(__name__)

# --------- Инициализация БД и каталога загрузок ----------
database.init_db()
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _resolve_in_output(relative: str) -> Path:
    """Преобразовать относительный путь в путь внутри output_dir."""
    base = Path(config.output_dir).resolve()
    target = (base / relative).resolve()
    # Защита от выхода за пределы output_dir
    if not target.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Path outside output_dir")
    return target


# --------- Маршруты ----------
@app.post("/upload")
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
        lang = language or config.tesseract_lang
        text = extract_text(temp_path, language=lang)
        folder_tree = get_folder_tree(config.output_dir)
        meta_result = metadata_generation.generate_metadata(text, folder_tree=folder_tree)
        metadata = meta_result["metadata"]
        metadata["extracted_text"] = text
        metadata["language"] = lang
        embedding = get_embedding(text)

        # Раскладываем файл по директориям без создания недостающих
        dest_path, missing = place_file(
            str(temp_path),
            metadata,
            config.output_dir,
            dry_run=dry_run,
            create_missing=False,
        )

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
            embedding=embedding,
        )
        return {"id": file_id, "status": "pending", "missing": missing}

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
    )

    return {
        "id": file_id,
        "filename": file.filename,
        "metadata": metadata,
        "path": str(dest_path),
        "status": status,
        "missing": [],
        "prompt": meta_result.get("prompt"),
        "raw_response": meta_result.get("raw_response"),
        "embedding": embedding,
    }


@app.post("/upload/images")
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
        tmp_pdf = merge_images_to_pdf(image_paths)
        pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
        shutil.move(tmp_pdf, pdf_path)
    except Exception as exc:  # pragma: no cover
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.exception("Failed to merge images: %s", [f.filename for f in files])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    shutil.rmtree(temp_dir, ignore_errors=True)

    try:
        lang = language or config.tesseract_lang
        text = extract_text(pdf_path, language=lang)
        folder_tree = get_folder_tree(config.output_dir)
        meta_result = metadata_generation.generate_metadata(text, folder_tree=folder_tree)
        metadata = meta_result["metadata"]
        metadata["extracted_text"] = text
        metadata["language"] = lang
        embedding = get_embedding(text)

        dest_path, missing = place_file(
            str(pdf_path),
            metadata,
            config.output_dir,
            dry_run=dry_run,
            create_missing=False,
        )
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
        )
        return {"id": file_id, "status": "pending", "missing": missing, "sources": sources}

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
    )

    return {
        "id": file_id,
        "filename": pdf_path.name,
        "metadata": metadata,
        "path": str(dest_path),
        "status": status,
        "missing": [],
        "prompt": meta_result.get("prompt"),
        "raw_response": meta_result.get("raw_response"),
        "sources": sources,
        "embedding": embedding,
    }


@app.get("/metadata/{file_id}")
async def get_metadata(file_id: str):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return record["metadata"]


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.get("path", ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=path.name)


@app.get("/preview/{file_id}")
async def preview_file(file_id: str):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.get("path", ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    content_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=content_type or "application/octet-stream")


@app.get("/files/{file_id}/details")
async def get_file_details(file_id: str):
    record = database.get_details(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return record


@app.get("/files")
async def list_files():
    return database.list_files()


@app.get("/search/semantic")
async def semantic_search(q: str):
    query_vec = get_embedding(q)
    results = []
    for rec in database.list_files():
        vec = rec.get("embedding")
        if not vec:
            continue
        score = cosine_similarity(query_vec, vec)
        results.append({"id": rec["id"], "filename": rec["filename"], "similarity": score})
    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results


@app.patch("/files/{file_id}")
async def update_file(file_id: str, data: dict = Body(...)):
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    metadata_updates = data.get("metadata") or {}
    new_metadata = record.get("metadata", {}).copy()
    if metadata_updates:
        new_metadata.update(metadata_updates)
    path_param = data.get("path")
    status = data.get("status")
    prompt = data.get("prompt")
    raw_response = data.get("raw_response")
    missing = data.get("missing")

    old_path = Path(record.get("path", ""))
    if not old_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    dest_path = old_path

    if metadata_updates and not path_param:
        old_json = old_path.with_suffix(old_path.suffix + ".json")
        if old_json.exists():
            old_json.unlink()
        dest_path, _ = place_file(
            old_path,
            new_metadata,
            config.output_dir,
            dry_run=False,
            create_missing=True,
        )
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
            json.dump(new_metadata, f, ensure_ascii=False, indent=2)

    database.update_file(
        file_id,
        metadata=new_metadata if metadata_updates else None,
        path=str(dest_path) if (metadata_updates or path_param) else None,
        status=status,
        prompt=prompt,
        raw_response=raw_response,
        missing=missing,
    )
    return database.get_file(file_id)


@app.get("/folder-tree")
async def folder_tree():
    """Вернуть структуру папок в выходном каталоге."""
    return get_folder_tree(config.output_dir)


@app.post("/folders")
async def create_folder(path: str):
    """Создать каталог внутри output_dir."""
    target = _resolve_in_output(path)
    if target.exists():
        raise HTTPException(status_code=409, detail="Folder already exists")
    target.mkdir(parents=True, exist_ok=False)
    return get_folder_tree(config.output_dir)


@app.patch("/folders/{folder_path:path}")
async def rename_folder(folder_path: str, new_name: str):
    src = _resolve_in_output(folder_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Folder not found")
    dest_relative = str(Path(folder_path).parent / new_name)
    dest = _resolve_in_output(dest_relative)
    if dest.exists():
        raise HTTPException(status_code=409, detail="Target already exists")
    src.rename(dest)
    return get_folder_tree(config.output_dir)


@app.delete("/folders/{folder_path:path}")
async def delete_folder(folder_path: str):
    target = _resolve_in_output(folder_path)
    base = Path(config.output_dir).resolve()
    if target == base:
        raise HTTPException(status_code=400, detail="Cannot delete root folder")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Folder not found")
    shutil.rmtree(target)
    return get_folder_tree(config.output_dir)


# ---------- ЕДИНЫЙ finalize ----------
@app.post("/files/{file_id}/finalize")
async def finalize_file(
    file_id: str,
    missing: list[str] | None = Body(default=None),
):
    """
    Завершить обработку «отложенного» файла:
    - при наличии `missing` — создать указанные каталоги внутри output_dir;
    - перенести файл в целевую структуру (create_missing=True);
    - обновить запись в БД.
    """
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if record.get("status") != "pending":
        # Возвращаем текущую запись, ничего не делаем
        return record

    # Если фронт подсказал недостающие, создадим их тут (без дергания собственного эндпоинта)
    if missing:
        for rel in missing:
            target = _resolve_in_output(rel)
            target.mkdir(parents=True, exist_ok=True)

    # Путь к временно загруженному файлу
    temp_path = record.get("path")
    if not temp_path:
        # Фолбэк: старый путь формата uploads/<uuid>_<filename>
        temp_path = str(UPLOAD_DIR / f"{file_id}_{record['filename']}")

    dest_path, still_missing = place_file(
        str(temp_path),
        record["metadata"],
        config.output_dir,
        dry_run=False,
        create_missing=True,
    )

    database.update_file(
        file_id,
        record["metadata"],
        str(dest_path),
        "processed",
        record.get("prompt"),
        record.get("raw_response"),
        still_missing,
    )
    return database.get_file(file_id)
