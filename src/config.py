from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:  # pydantic v2
    from pydantic_settings import BaseSettings  # type: ignore[import]
except Exception:  # pragma: no cover
    try:  # pydantic v1
        from pydantic import BaseSettings  # type: ignore[assignment]
    except Exception:  # pragma: no cover - minimal fallback
        class BaseSettings:  # type: ignore[misc]
            class Config:
                env_file = None
                env_file_encoding = "utf-8"
                case_sensitive = False

            def __init__(self, **values):
                data: dict[str, str] = {}
                env_file = getattr(self.Config, "env_file", None)
                if env_file and Path(env_file).exists():
                    for line in Path(env_file).read_text(encoding=getattr(self.Config, "env_file_encoding", "utf-8")).splitlines():
                        if not line or line.lstrip().startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        data[k.strip()] = v.strip()
                for field, _ in getattr(self, "__annotations__", {}).items():
                    env_name = field.upper() if not getattr(self.Config, "case_sensitive", False) else field
                    val = os.getenv(env_name)
                    if val is None and not getattr(self.Config, "case_sensitive", False):
                        val = os.getenv(field)
                    if val is None:
                        val = data.get(env_name) or data.get(field)
                    if val is None:
                        val = getattr(self.__class__, field, None)
                    setattr(self, field, values.get(field, val))


class Settings(BaseSettings):
    """Configuration settings for the application."""

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


config = Settings()

__all__ = ["Settings", "config"]
