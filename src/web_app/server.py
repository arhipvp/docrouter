from __future__ import annotations

import logging
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
from file_sorter import place_file
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
        metadata = metadata_generation.generate_metadata(text)
        metadata["extracted_text"] = text
        metadata["language"] = lang

        # Раскладываем файл по директориям
        dest_path = place_file(str(temp_path), metadata, config.output_dir, dry_run=dry_run)

    except Exception as exc:  # pragma: no cover
        logger.exception("Upload/processing failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    status = "dry_run" if dry_run else "processed"

    # Сохраняем запись в БД
    database.add_file(file_id, metadata, str(dest_path), status)

    return {
        "id": file_id,
        "metadata": metadata,
        "path": str(dest_path),
        "status": status,
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
