from __future__ import annotations

import logging
from pathlib import Path
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import threading
import importlib
try:
    from fastapi.templating import Jinja2Templates
except Exception:  # pragma: no cover
    Jinja2Templates = None  # type: ignore[misc,assignment]

from config import config  # type: ignore  # noqa: F401
from . import db as database
from .routes import upload, files, folders, chat

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
def startup() -> None:
    """Инициализировать базу данных перед обработкой запросов."""
    database.init_db()

    def _load_plugins() -> None:
        try:
            file_utils = importlib.import_module("file_utils")
            file_utils.load_plugins()
        except Exception:  # pragma: no cover - ошибки плагинов не критичны
            logger.warning("Plugin loading failed", exc_info=True)

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
