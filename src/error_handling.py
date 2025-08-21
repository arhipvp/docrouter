from __future__ import annotations

import json
import logging
import shutil
import traceback
from pathlib import Path
from typing import Optional

# Настройка логирования (мягкая зависимость)
try:
    from config import LOG_LEVEL  # алиас из нашего Config-модуля
except Exception:
    LOG_LEVEL = "INFO"

try:
    from logging_config import setup_logging as _setup_logging  # pragma: no cover - optional
except Exception:
    _setup_logging = None

# Инициализация логгера
logger = logging.getLogger(__name__)
if _setup_logging:
    # Если есть модуль конфигурации логирования — используем его.
    _setup_logging(LOG_LEVEL, None)
else:
    # Базовая настройка на случай отсутствия кастомного конфигуратора
    level = getattr(logging, str(LOG_LEVEL).upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def log_exception(exc: Exception, *, file: Optional[Path] = None) -> None:
    """Записать исключение в лог с опциональным контекстом файла."""
    if file:
        logger.error("Error processing %s", file, exc_info=exc)
    else:
        logger.error("Unhandled exception", exc_info=exc)


def handle_error(file_path: str | Path, exception: Exception,
                 *, unsorted_dir: str | Path = "Unsorted", errors_dir: str | Path = "errors") -> None:
    """Залогировать *exception*, переместить *file_path* в ``Unsorted`` и сохранить JSON с деталями.

    JSON пишется в ``errors/<filename>.json``, где ``<filename>`` — исходное имя файла.
    """
    src = Path(file_path)
    logger.error("Ошибка при обработке %s: %s", src, exception)

    # Перемещаем файл в Unsorted/
    try:
        unsorted = Path(unsorted_dir)
        unsorted.mkdir(parents=True, exist_ok=True)
        dest = unsorted / src.name
        if src.exists():
            shutil.move(str(src), str(dest))
    except Exception as move_exc:  # не даём упасть при ошибке перемещения
        logger.exception("Не удалось переместить файл %s в %s: %s", src, unsorted, move_exc)

    # Сохраняем сведения об ошибке
    try:
        errors = Path(errors_dir)
        errors.mkdir(parents=True, exist_ok=True)
        error_info = {
            "file": src.name,
            "error": str(exception),
            "traceback": "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)),
        }
        error_file = errors / f"{src.name}.json"
        with error_file.open("w", encoding="utf-8") as f:
            json.dump(error_info, f, ensure_ascii=False, indent=2)
    except Exception as write_exc:
        logger.exception("Не удалось записать JSON с ошибкой для %s: %s", src, write_exc)


__all__ = ["log_exception", "handle_error"]
