from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import load_config
from logging_config import setup_logging
from file_utils import extract_text
from file_sorter import place_file
import metadata_generation
from . import database

app = FastAPI()

# Статика (форма загрузки)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def serve_index() -> FileResponse:
    """Отдать форму загрузки."""
    return FileResponse(STATIC_DIR / "index.html")


# Конфиг и логирование
config = load_config()
try:
    # если setup_logging доступен — используем его
    setup_logging(config.log_level, None)  # type: ignore[arg-type]
except Exception:
    logging.basicConfig(level=getattr(logging, str(config.log_level).upper(), logging.INFO))

logger = logging.getLogger(__name__)

# Инициализация БД и каталога загрузок
database.init_db()
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), dry_run: bool = False):
    """Загрузить файл и обработать его."""
    file_id = str(uuid.uuid4())
    temp_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as dest:
            dest.write(contents)

        # Извлечение текста + генерация метаданных
        text = extract_text(temp_path, language=config.tesseract_lang)
        metadata = metadata_generation.generate_metadata(text)
        metadata["extracted_text"] = text

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
    # при желании можно добавить filename=path.name
    return FileResponse(path)
