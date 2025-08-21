from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from functools import lru_cache

import yaml


DEFAULTS = {
    "level": "INFO",
    "file": "docrouter.log",
    "max_bytes": 1024 * 1024,
    "backup_count": 3,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}


@lru_cache()
def _load_config() -> dict:
    """Загрузить конфигурацию из YAML."""
    config_path = os.environ.get("DOCROUTER_CONFIG", "config.yml")
    try:
        with open(Path(config_path), encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}


@lru_cache()
def _configure_root() -> int:
    """Настроить корневой логгер и вернуть выбранный уровень."""
    cfg = _load_config().get("logging", {})
    level_name = str(cfg.get("level", DEFAULTS["level"])).upper()
    level = getattr(logging, level_name, logging.INFO)

    log_file = Path(cfg.get("file", DEFAULTS["file"]))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = int(cfg.get("max_bytes", DEFAULTS["max_bytes"]))
    backup_count = int(cfg.get("backup_count", DEFAULTS["backup_count"]))
    fmt = cfg.get("format", DEFAULTS["format"])

    handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)
    return level


def get_logger(name: str) -> logging.Logger:
    """Получить настроенный логгер по имени."""
    level = _configure_root()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
