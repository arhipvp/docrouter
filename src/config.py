from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Configuration settings for the application."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    log_level: str = "INFO"
    tesseract_lang: str = "eng"
    tesseract_cmd: Optional[str] = None
    output_dir: str = "Archive"
    general_folder_name: str = "Shared"
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: Optional[str] = None
    openrouter_model: Optional[str] = None
    openrouter_site_url: Optional[str] = None
    openrouter_site_name: Optional[str] = None
    db_url: Optional[str] = None
    docrouter_reset_db: bool = Field(default=False, alias="DOCROUTER_RESET_DB")


# --------- Backward compatibility / convenient aliases ---------
config = Config()

LOG_LEVEL = config.log_level
TESSERACT_LANG = config.tesseract_lang
TESSERACT_CMD = config.tesseract_cmd
OUTPUT_DIR = config.output_dir
GENERAL_FOLDER_NAME = config.general_folder_name
OPENROUTER_API_KEY = config.openrouter_api_key
OPENROUTER_BASE_URL = config.openrouter_base_url
OPENROUTER_MODEL = config.openrouter_model
OPENROUTER_SITE_URL = config.openrouter_site_url
OPENROUTER_SITE_NAME = config.openrouter_site_name
DB_URL = config.db_url
DOCROUTER_RESET_DB = config.docrouter_reset_db

__all__ = [
    "Config",
    "config",
    "LOG_LEVEL",
    "TESSERACT_LANG",
    "TESSERACT_CMD",
    "OUTPUT_DIR",
    "GENERAL_FOLDER_NAME",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_MODEL",
    "OPENROUTER_SITE_URL",
    "OPENROUTER_SITE_NAME",
    "DB_URL",
    "DOCROUTER_RESET_DB",
]
