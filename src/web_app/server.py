from __future__ import annotations

import logging
import os
import secrets
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
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


# --------- Аутентификация (HTTP Basic) ----------
security = HTTPBasic()


def check_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Проверить учетные данные из HTTP Basic auth."""
    user = os.getenv("DOCROUTER_USER", "")
    password = os.getenv("DOCROUTER_PASS", "")
    valid_user = secrets.compare_digest(credentials.username, user)
    valid_pass = secrets.compare_digest(credentials.password, password)
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
    dry_run: bool = False,
    _: str = Depends(check_credentials),
):
    """Загрузить файл и обработать его (защищено Basic Auth)."""
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
async def get_metadata(file_id: str, _: str = Depends(check_credentials)):
    """Получить сохранённые метаданные по ID файла (защищено Basic Auth)."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return record["metadata"]


@app.get("/download/{file_id}")
async def download_file(file_id: str, _: str = Depends(check_credentials)):
    """Скачать обработанный файл по ID (защищено Basic Auth)."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.get("path", ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=path.name)
