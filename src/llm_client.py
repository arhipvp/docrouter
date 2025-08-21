import os
from pathlib import Path
import requests
import yaml

from .metadata_schema import validate_metadata

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _load_config() -> dict:
    """Загружает конфигурацию из YAML-файла.

    Путь к файлу можно переопределить переменной окружения
    ``DOCROUTER_CONFIG``.
    """
    config_path = os.environ.get("DOCROUTER_CONFIG", "config.yml")
    with open(Path(config_path), encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def analyze_text(text: str) -> dict:
    """Отправляет текст в OpenRouter и возвращает распарсенный JSON.

    Модель берётся из конфигурационного файла. Возможные ошибки сети и
    невалидный JSON оборачиваются в ``RuntimeError``.
    """
    config = _load_config()
    model = config.get("model", "")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
    }

    try:
        response = requests.post(
            OPENROUTER_URL, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()
    except requests.RequestException as exc:  # ошибки сети
        raise RuntimeError("OpenRouter request failed") from exc

    try:
        data = response.json()
    except ValueError as exc:  # невалидный JSON
        raise RuntimeError("Invalid JSON received from OpenRouter") from exc

    return validate_metadata(data)
