"""Входная точка для запуска сервиса DocRouter.

Запускает сервер FastAPI, определённый в модуле ``web_app.server``.
Параметры задаются через переменные окружения, что упрощает запуск.
"""

from __future__ import annotations

import logging
import os
import sys

import uvicorn
from docrouter.config import LOG_LEVEL  # type: ignore
from docrouter.logging_config import setup_logging  # type: ignore
from docrouter.web_app.server import app

logger = logging.getLogger(__name__)


def main() -> None:
    """Точка входа для запуска сервера.

    Значения берутся из переменных окружения:
    ``HOST`` (по умолчанию ``0.0.0.0``),
    ``PORT`` (по умолчанию ``8000``)
    и ``RELOAD`` (``true``/``false``, по умолчанию ``false``).
    """

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}

    # Настраиваем логирование согласно конфигу
    setup_logging(LOG_LEVEL, None)
    logger.info("Starting FastAPI server on %s:%s", host, port)

    try:
        uvicorn.run(app, host=host, port=port, reload=reload)
    except Exception:
        logger.exception("Не удалось запустить сервер")
        sys.exit(1)


if __name__ == "__main__":
    main()
