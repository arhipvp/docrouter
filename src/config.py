from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration settings for the application."""
    log_level: str = "INFO"
    tesseract_lang: str = "eng"
    output_dir: str = "Archive"
    general_folder_name: str = "Shared"
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: Optional[str] = None
    openrouter_model: Optional[str] = None
    openrouter_site_url: Optional[str] = None
    openrouter_site_name: Optional[str] = None
    db_url: Optional[str] = None


def _get_first_env(*keys: str, default: Optional[str] = None) -> Optional[str]:
    """Вернуть первое найденное значение из переменных окружения (по списку ключей)."""
    for k in keys:
        val = os.getenv(k)
        if val is not None:
            return val
    return default


def load_config() -> Config:
    """
    Загружает конфигурацию.
    - Если есть pydantic: читает .env и переменные окружения (нижний/верхний регистр).
    - Всегда поддерживает перекрытие через UPPER_CASE переменные.
    """
    # База из окружения (верхний/нижний регистры на всякий случай)
    base = Config(
        log_level=_get_first_env("LOG_LEVEL", "log_level", default="INFO") or "INFO",
        tesseract_lang=_get_first_env("TESSERACT_LANG", "tesseract_lang", default="eng") or "eng",
        output_dir=_get_first_env("OUTPUT_DIR", "output_dir", default="Archive") or "Archive",
        general_folder_name=_get_first_env("GENERAL_FOLDER_NAME", "general_folder_name", default="Shared") or "Shared",
        openrouter_api_key=_get_first_env("OPENROUTER_API_KEY", "openrouter_api_key"),
        openrouter_base_url=_get_first_env("OPENROUTER_BASE_URL", "openrouter_base_url"),
        openrouter_model=_get_first_env("OPENROUTER_MODEL", "openrouter_model"),
        openrouter_site_url=_get_first_env("OPENROUTER_SITE_URL", "openrouter_site_url"),
        openrouter_site_name=_get_first_env("OPENROUTER_SITE_NAME", "openrouter_site_name"),
        db_url=_get_first_env("DB_URL", "db_url"),
    )

    # Пытаемся подхватить .env через pydantic (если установлен)
    try:
        from pydantic import BaseSettings, Field  # type: ignore

        class Settings(BaseSettings):
            openrouter_api_key: Optional[str] = Field(default=None, env=["openrouter_api_key", "OPENROUTER_API_KEY"])
            openrouter_base_url: Optional[str] = Field(default=None, env=["openrouter_base_url", "OPENROUTER_BASE_URL"])
            openrouter_model: Optional[str] = Field(default=None, env=["openrouter_model", "OPENROUTER_MODEL"])
            openrouter_site_url: Optional[str] = Field(default=None, env=["openrouter_site_url", "OPENROUTER_SITE_URL"])
            openrouter_site_name: Optional[str] = Field(default=None, env=["openrouter_site_name", "OPENROUTER_SITE_NAME"])
            db_url: Optional[str] = Field(default=None, env=["db_url", "DB_URL"])
            log_level: str = Field(default="INFO", env=["log_level", "LOG_LEVEL"])
            tesseract_lang: str = Field(default="eng", env=["tesseract_lang", "TESSERACT_LANG"])
            output_dir: str = Field(default="Archive", env=["output_dir", "OUTPUT_DIR"])
            general_folder_name: str = Field(default="Shared", env=["general_folder_name", "GENERAL_FOLDER_NAME"])

            class Config:  # pydantic v1 совместимость
                env_file = ".env"
                env_file_encoding = "utf-8"

        s = Settings()

        cfg = Config(
            log_level=s.log_level or base.log_level,
            tesseract_lang=s.tesseract_lang or base.tesseract_lang,
            output_dir=s.output_dir or base.output_dir,
            openrouter_api_key=s.openrouter_api_key or base.openrouter_api_key,
            openrouter_base_url=s.openrouter_base_url or base.openrouter_base_url,
            openrouter_model=s.openrouter_model or base.openrouter_model,
            openrouter_site_url=s.openrouter_site_url or base.openrouter_site_url,
            openrouter_site_name=s.openrouter_site_name or base.openrouter_site_name,
            db_url=s.db_url or base.db_url,
            general_folder_name=s.general_folder_name or base.general_folder_name,
        )

        # Финальный приоритет: UPPER_CASE переменные окружения (если заданы)
        cfg.log_level = _get_first_env("LOG_LEVEL", default=cfg.log_level) or cfg.log_level
        cfg.tesseract_lang = _get_first_env("TESSERACT_LANG", default=cfg.tesseract_lang) or cfg.tesseract_lang
        cfg.output_dir = _get_first_env("OUTPUT_DIR", default=cfg.output_dir) or cfg.output_dir
        cfg.openrouter_api_key = _get_first_env("OPENROUTER_API_KEY", default=cfg.openrouter_api_key)
        cfg.openrouter_base_url = _get_first_env("OPENROUTER_BASE_URL", default=cfg.openrouter_base_url)
        cfg.openrouter_model = _get_first_env("OPENROUTER_MODEL", default=cfg.openrouter_model)
        cfg.openrouter_site_url = _get_first_env("OPENROUTER_SITE_URL", default=cfg.openrouter_site_url)
        cfg.openrouter_site_name = _get_first_env("OPENROUTER_SITE_NAME", default=cfg.openrouter_site_name)
        cfg.db_url = _get_first_env("DB_URL", default=cfg.db_url)
        cfg.general_folder_name = _get_first_env("GENERAL_FOLDER_NAME", default=cfg.general_folder_name) or cfg.general_folder_name

    except Exception:
        # pydantic недоступен — используем только окружение
        cfg = base

    # Нормализация
    cfg.log_level = (cfg.log_level or "INFO").upper().strip()
    cfg.output_dir = (cfg.output_dir or "Archive").strip()
    cfg.general_folder_name = (cfg.general_folder_name or "Shared").strip()

    return cfg


# --------- Backward compatibility / удобные алиасы ---------
config: Config = load_config()

LOG_LEVEL = config.log_level            # совместимо с старым кодом
TESSERACT_LANG = config.tesseract_lang
OUTPUT_DIR = config.output_dir
GENERAL_FOLDER_NAME = config.general_folder_name
OPENROUTER_API_KEY = config.openrouter_api_key
OPENROUTER_BASE_URL = config.openrouter_base_url
OPENROUTER_MODEL = config.openrouter_model
OPENROUTER_SITE_URL = config.openrouter_site_url
OPENROUTER_SITE_NAME = config.openrouter_site_name
DB_URL = config.db_url

__all__ = [
    "Config",
    "load_config",
    "config",
    "LOG_LEVEL",
    "TESSERACT_LANG",
    "OUTPUT_DIR",
    "GENERAL_FOLDER_NAME",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_MODEL",
    "OPENROUTER_SITE_URL",
    "OPENROUTER_SITE_NAME",
    "DB_URL",
]
