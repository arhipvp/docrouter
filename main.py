"""Входная точка для запуска сервиса DocRouter.

Запускает сервер FastAPI, определённый в модуле ``web_app.server``.
Команда позволяет указать адрес и порт, а также включить автоматическую
перезагрузку кода при разработке.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Делаем пакет ``src`` доступным для импортов при запуске из корня репозитория
sys.path.append(str(Path(__file__).resolve().parent / "src"))

import uvicorn
from config import LOG_LEVEL  # type: ignore
from logging_config import setup_logging  # type: ignore

logger = logging.getLogger(__name__)


def main() -> None:
    """Точка входа CLI.

    Запускает сервер FastAPI с указанными параметрами.
    """

    parser = argparse.ArgumentParser(description="Start DocRouter FastAPI server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable autoreload")
    args = parser.parse_args()

    # Настраиваем логирование согласно конфигу
    setup_logging(LOG_LEVEL, None)
    logger.info("Starting FastAPI server on %s:%s", args.host, args.port)

    uvicorn.run("web_app.server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()

