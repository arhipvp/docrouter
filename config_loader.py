import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv
import yaml


@dataclass
class AppConfig:
    """Основная конфигурация приложения."""

    categories: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    vendors: List[str] = field(default_factory=list)


def load_config(config_path: str = "config.yml") -> AppConfig:
    """Загрузить конфигурацию приложения из YAML-файла."""
    data = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    return AppConfig(
        categories=data.get("categories", []),
        people=data.get("people", []),
        vendors=data.get("vendors", []),
    )


def load_openrouter_settings():
    """Загрузить настройки OpenRouter из переменных окружения."""
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openrouter/llama3-8b")
    max_concurrency = int(os.getenv("LLM_MAX_CONCURRENCY", "2"))
    return {
        "api_key": api_key,
        "model": model,
        "max_concurrency": max_concurrency,
    }
