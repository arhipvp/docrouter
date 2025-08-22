from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
try:
    from fastapi.templating import Jinja2Templates
except Exception:  # pragma: no cover
    Jinja2Templates = None  # type: ignore[misc,assignment]

from config import load_config
from logging_config import setup_logging
from file_utils import extract_text
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
    # Фолбэк без Jinja2 — просто отдаём содержимое файла как HTML.
    index_path = TEMPLATES_DIR / "index.html"
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

    # Статус
    if dry_run:
        status = "dry_run"
    elif missing:
        status = "pending"
    else:
        status = "processed"

    # Сохраняем запись в БД
    database.add_file(
        file_id,
        file.filename,
        metadata,
        str(dest_path),
        status,
        meta_result.get("prompt"),
        meta_result.get("raw_response"),
        missing,
    )

    return {
        "id": file_id,
        "filename": file.filename,
        "metadata": metadata,
        "path": str(dest_path),
        "status": status,
        "missing": missing,
        "prompt": meta_result.get("prompt"),
        "raw_response": meta_result.get("raw_response"),
    }


@app.get("/metadata/{file_id}")
async def get_metadata(file_id: str):
    """Получить сохранённые метаданные по ID файла."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return record["metadata"]


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """Скачать обработанный файл по ID."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.get("path", ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=path.name)


@app.get("/files/{file_id}/details")
async def get_file_details(file_id: str):
    """Вернуть полную запись о файле."""
    record = database.get_details(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return record


@app.get("/files")
async def list_files():
    """Вернуть список всех загруженных файлов."""
    return database.list_files()


@app.get("/folder-tree")
async def folder_tree():
    """Вернуть структуру папок в выходном каталоге.

    Каждый элемент содержит поля ``name``, ``path`` и ``children``.
    """
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
    """Переименовать каталог."""
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
    """Удалить каталог."""
    target = _resolve_in_output(folder_path)
    base = Path(config.output_dir).resolve()
    if target == base:
        raise HTTPException(status_code=400, detail="Cannot delete root folder")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Folder not found")
    shutil.rmtree(target)
    return get_folder_tree(config.output_dir)


@app.post("/files/{file_id}/finalize")
async def finalize_file(file_id: str):
    """Переместить ранее загруженный файл после создания недостающих папок."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if record.get("status") != "pending":
        return record

    src = UPLOAD_DIR / f"{file_id}_{record['filename']}"
    dest_path, missing = place_file(
        src,
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
        missing,
    )
    return database.get_file(file_id)
