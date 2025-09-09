from __future__ import annotations

import logging
from pathlib import Path
import os
import asyncio
import importlib
from types import ModuleType

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import threading

try:
    from fastapi.templating import Jinja2Templates
except Exception:  # pragma: no cover
    Jinja2Templates = None  # type: ignore[misc,assignment]

from config import config  # type: ignore  # noqa: F401
from . import db as database
from .routes import upload, files, folders, chat

app = FastAPI()

# --------- Ленивые импорты тяжёлых модулей ----------
_file_utils: ModuleType | None = None
_metadata_generation: ModuleType | None = None


def _load_file_utils() -> ModuleType:
    """Импортировать ``file_utils`` по требованию."""
    global _file_utils
    if _file_utils is None:
        _file_utils = importlib.import_module("file_utils")
    return _file_utils


def _load_metadata_generation() -> ModuleType:
    """Импортировать ``metadata_generation`` по требованию."""
    global _metadata_generation
    if _metadata_generation is None:
        _metadata_generation = importlib.import_module("metadata_generation")
    return _metadata_generation


def extract_text(*args, **kwargs):
    return _load_file_utils().extract_text(*args, **kwargs)


def merge_images_to_pdf(*args, **kwargs):
    return _load_file_utils().merge_images_to_pdf(*args, **kwargs)


async def translate_text(*args, **kwargs):
    return await _load_file_utils().translate_text(*args, **kwargs)


class _MetadataGenerationProxy:
    def __getattr__(self, name: str):
        return getattr(_load_metadata_generation(), name)


metadata_generation = _MetadataGenerationProxy()

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


logger = logging.getLogger(__name__)


def __getattr__(name: str):
    """Лениво импортировать тяжёлые зависимости при обращении."""
    if name in {"extract_text", "merge_images_to_pdf", "translate_text"}:
        utils = importlib.import_module("file_utils")
        return getattr(utils, name)
    if name == "metadata_generation":
        return importlib.import_module("metadata_generation")
    raise AttributeError(f"module {__name__} has no attribute {name}")

# --------- Инициализация БД ----------


@app.on_event("startup")
async def startup() -> None:
    """Инициализировать базу данных и отложенно загрузить плагины."""
    await database.run_db(database.init_db)

    def _load_plugins() -> None:
        try:
            _load_file_utils().load_plugins()
            from plugins import load_plugins as _load_plugins
            _load_plugins()
        except Exception:  # pragma: no cover - плагины не обязательны
            logger.debug("Plugin loading skipped", exc_info=True)

    # Фоновая загрузка плагинов, чтобы не блокировать старт
    threading.Thread(target=_load_plugins, name="plugin-loader", daemon=True).start()


@app.on_event("shutdown")
def _shutdown() -> None:
    database.close_db()

# --------- Подключение маршрутов ----------
app.include_router(upload.router)
app.include_router(files.router)
app.include_router(folders.router)
app.include_router(chat.router)


def main() -> None:
    """Запустить сервер с параметрами из переменных окружения."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}
    logger.info("Starting FastAPI server on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
