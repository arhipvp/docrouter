from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""

    LOG_LEVEL: str = "INFO"


config = Config()
LOG_LEVEL = config.LOG_LEVEL
