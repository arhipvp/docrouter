from typing import Optional


def load_config():
    """Загружает настройки из файла .env и переменных окружения."""
    from pydantic import BaseSettings

    class Settings(BaseSettings):
        openrouter_api_key: Optional[str] = None
        db_url: Optional[str] = None
        log_level: str = "INFO"
        tesseract_lang: str = "eng"

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

    return Settings()
