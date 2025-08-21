from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class Config:
    """Configuration settings for the application."""
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    TESSERACT_LANG: str = os.getenv("TESSERACT_LANG", "eng")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "Archive")


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config()
