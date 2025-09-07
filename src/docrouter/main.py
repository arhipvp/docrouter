"""Входная точка для запуска сервиса DocRouter."""
from __future__ import annotations

import logging
import os
import sys

import uvicorn

from docrouter.config import config
from docrouter.logging_config import setup_logging
from docrouter.web_app.server import app

logger = logging.getLogger(__name__)


def main() -> None:
    """Запуск сервера FastAPI с настройками из окружения."""
    cfg = config

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}

    setup_logging(cfg.log_level, None)
    logger.info("Starting FastAPI server on %s:%s", host, port)

    try:
        uvicorn.run(app, host=host, port=port, reload=reload)
    except Exception:
        logger.exception("Не удалось запустить сервер")
        sys.exit(1)
