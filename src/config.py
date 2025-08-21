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
    openrouter_api_key: Optional[str] = None
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
    # Базовые значения из окружения (верхний регистр — совместимость со старым кодом)
    base = Config(
        log_level=_get_first_env("LOG_LEVEL", "log_level", default="INFO") or "INFO",
        tesseract_lang=_get_first_env("TESSERACT_LANG", "tesseract_lang", default="eng") or "eng",
        output_dir=_get_first_env("OUTPUT_DIR", "output_dir", default="Archive") or "Archive",
        openrouter_api_key=_get_first_env("OPENROUTER_API_KEY", "openrouter_api_key"),
        db_url=_get_first_env("DB_URL", "db_url"),
    )

    # Попытка загрузить .env через pydantic (если установлен)
    try:
        from pydantic import BaseSettings, Field  # type: ignore

        class Settings(BaseSettings):
            openrouter_api_key: Optional[str] = Field(default=None, env=["openrouter_api_key", "OPENROUTER_API_KEY"])
            db_url: Optional[str] = Field(default=None, env=["db_url", "DB_URL"])
            log_level: str = Field(default="INFO", env=["log_level", "LOG_LEVEL"])
            tesseract_lang: str = Field(default="eng", env=["tesseract_lang", "TESSERACT_LANG"])
            output_dir: str = Field(default="Archive", env=["output_dir", "OUTPUT_DIR"])

            class Config:  # pydantic v1
                env_file = ".env"
                env_file_encoding = "utf-8"

        s = Settings()

        # Значения из Settings перекрывают base, затем снова даём шанс UPPER_CASE env (если нужно)
        cfg = Config(
            log_level=s.log_level or base.log_level,
            tesseract_lang=s.tesseract_lang or base.tesseract_lang,
            output_dir=s.output_dir or base.output_dir,
            openrouter_api_key=s.openrouter_api_key or base.openrouter_api_key,
            db_url=s.db_url or base.db_url,
        )

        # Финальное перекрытие через UPPER_CASE переменные (если заданы)
        cfg.log_level = _get_first_env("LOG_LEVEL", default=cfg.log_level) or cfg.log_level
        cfg.tesseract_lang = _get_first_env("TESSERACT_LANG", default=cfg.tesseract_lang) or cfg.tesseract_lang
        cfg.output_dir = _get_first_env("OUTPUT_DIR", default=cfg.output_dir) or cfg.output_dir
        cfg.openrouter_api_key = _get_first_env("OPENROUTER_API_KEY", default=cfg.openrouter_api_key)
        cfg.db_url = _get_first_env("DB_URL", default=cfg.db_url)

        # Чуть-чуть нормализации
        cfg.log_level = (cfg.log_level or "INFO").upper().strip()
        cfg.output_dir = (cfg.output_dir or "Archive").strip()

        return cfg

    except Exception:
        # pydantic не установлен — используем только окружение
        base.log_level = (base.log_level or "INFO").upper().strip()
        base.output_dir = (base.output_dir or "Archive").strip()
        return base
