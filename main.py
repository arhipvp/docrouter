"""Входная точка для запуска сервиса DocRouter.

Запускает сервер FastAPI, определённый в модуле ``web_app.server``.
Параметры задаются через переменные окружения, что упрощает запуск.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Поддержка запуска из исходников: добавляем ``src`` в ``sys.path``
sys.path.append(str(Path(__file__).resolve().parent / "src"))

import uvicorn
from config import config  # type: ignore
from logging_config import setup_logging  # type: ignore

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
    setup_logging(config.log_level, None)
    logger.info("Starting FastAPI server on %s:%s", host, port)

    try:
        uvicorn.run("web_app.server:app", host=host, port=port, reload=reload)
    except Exception:
        logger.exception("Не удалось запустить сервер")
        sys.exit(1)


if __name__ == "__main__":
    main()

