"""
Metadata generation module.

This module предоставляет высокоуровневую функцию :func:`generate_metadata`,
которая использует LLM через OpenRouter. При необходимости можно подключить
иные анализаторы.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Callable

import httpx

from models import Metadata
from prompt_templates import build_metadata_prompt

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_SITE_NAME,
    OPENROUTER_SITE_URL,
)

from services.openrouter import OpenRouterError
from file_utils.mrz import parse_mrz


logger = logging.getLogger(__name__)

_ANALYZER_REGISTRY: Dict[str, type["MetadataAnalyzer"]] = {}


def register_analyzer(name: str) -> Callable[[type["MetadataAnalyzer"]], type["MetadataAnalyzer"]]:
    """Декоратор для регистрации анализаторов метаданных."""
    def decorator(cls: type["MetadataAnalyzer"]) -> type["MetadataAnalyzer"]:
        _ANALYZER_REGISTRY[name] = cls
        return cls
    return decorator


def get_analyzer(name: str) -> type["MetadataAnalyzer"]:
    """Получить класс анализатора по имени."""
    return _ANALYZER_REGISTRY[name]


def _parse_person_from_text(text: str) -> Optional[str]:
    """Попытаться извлечь ФИО владельца из текста документа.

    Ориентируемся на ключевые слова "Фамилия", "Имя", "Отчество" и
    комбинируем найденные значения.
    """

    patterns = {
        "surname": r"Фамилия[:\s]+([A-Za-zА-Яа-яЁё-]+)",
        "name": r"Имя[:\s]+([A-Za-zА-Яа-яЁё-]+)",
        "patronymic": r"Отчество[:\s]+([A-Za-zА-Яа-яЁё-]+)",
    }

    found: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found[key] = match.group(1).strip()

    if not found:
        return None

    parts = [found.get("surname"), found.get("name"), found.get("patronymic")]
    person = " ".join(part for part in parts if part)
    return person or None


__all__ = [
    "generate_metadata",
    "MetadataAnalyzer",
    "OpenRouterAnalyzer",
    "OpenRouterError",
    "register_analyzer",
    "get_analyzer",
]


class MetadataAnalyzer(ABC):
    """Abstract base class for metadata analyzers."""

    @abstractmethod
    async def analyze(
        self,
        text: str,
        folder_tree: Optional[Dict[str, Any]] = None,
        file_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze *text* and return a dict with keys ``prompt``, ``raw_response`` and ``metadata``."""


@register_analyzer("openrouter")
class OpenRouterAnalyzer(MetadataAnalyzer):
    """Analyzer that delegates to an OpenRouter-hosted LLM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        site_url: Optional[str] = None,
        site_name: Optional[str] = None,
    ):
        self.api_key = api_key or OPENROUTER_API_KEY
        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY environment variable required")

        self.model = model or OPENROUTER_MODEL or "openai/chatgpt-4o-latest"
        self.base_url = base_url or OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
        self.api_url = self.base_url.rstrip("/") + "/chat/completions"
        self.site_url = site_url or OPENROUTER_SITE_URL or "https://github.com/docrouter"
        self.site_name = site_name or OPENROUTER_SITE_NAME or "DocRouter Metadata Generator"

    async def analyze(
        self,
        text: str,
        folder_tree: Optional[Dict[str, Any]] = None,
        file_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Единый шаблон промпта
        prompt = build_metadata_prompt(text, folder_tree=folder_tree, file_info=file_info)

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            # OpenRouter совместим с OpenAI; просим строгий JSON
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        logger.debug("OpenRouter payload: %s", payload)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
            logger.debug("OpenRouter response status %s: %s", response.status_code, response.text)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OpenRouter request failed: status=%s body=%s",
                exc.response.status_code if exc.response else None,
                exc.response.text if exc.response else None,
            )
            raise OpenRouterError(
                f"OpenRouter request failed: {exc.response.status_code if exc.response else ''}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("OpenRouter request failed: %s", exc)
            raise OpenRouterError("OpenRouter request failed") from exc

        # Парсинг JSON-ответа
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response from OpenRouter: %s", response.text[:800])
            raise OpenRouterError("Invalid (non-JSON) response from OpenRouter")

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected schema from OpenRouter: %s", data)
            raise OpenRouterError("Unexpected response schema from OpenRouter") from exc

        if not content or not content.strip():
            logger.error("Empty content from OpenRouter: %s", response.text)
            raise OpenRouterError("Empty response from OpenRouter")

        # Снимаем возможные ограды ```json
        txt = content.strip()
        if txt.startswith("```"):
            lines = txt.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            txt = "\n".join(lines).strip()

        try:
            metadata = json.loads(txt)
        except json.JSONDecodeError:
            logger.error("JSON decode error from OpenRouter content: %s", txt[:800])
            raise OpenRouterError("Invalid JSON from OpenRouter")

        return {"prompt": prompt, "raw_response": txt, "metadata": metadata}


async def generate_metadata(
    text: str,
    analyzer: Optional[MetadataAnalyzer] = None,
    *,
    folder_tree: Optional[Dict[str, Any]] = None,
    file_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate metadata for *text* using the provided *analyzer*.

    If *analyzer* is ``None`` the function creates an :class:`OpenRouterAnalyzer`.
    Любые ошибки при обращении к OpenRouter пробрасываются вызывающему коду.

    The returned dictionary always contains the following fields:
    ``category``, ``subcategory``, ``issuer``, ``person``, ``doc_type``,
    ``date``, ``amount``, ``counterparty``, ``document_number``, ``due_date``, ``currency``, ``tags``, ``tags_ru``,
    ``tags_en``, ``suggested_filename``, ``description``, ``needs_new_folder``.
    """
    if analyzer is None:
        analyzer = OpenRouterAnalyzer()

    result = await analyzer.analyze(text, folder_tree=folder_tree, file_info=file_info)
    metadata = result.get("metadata", {})

    defaults = {
        "category": None,
        "subcategory": None,
        "issuer": None,
        "person": None,
        "doc_type": None,
        "date": None,
        "date_of_birth": None,
        "expiration_date": None,
        "passport_number": None,
        "amount": None,
        "counterparty": None,
        "document_number": None,
        "due_date": None,
        "currency": None,
        "tags": [],
        "tags_ru": [],
        "tags_en": [],
        "suggested_filename": None,
        "description": None,
        "needs_new_folder": False,
    }
    defaults.update(metadata or {})

    # Вытаскиваем stem для suggested_name
    suggested_filename = defaults.get("suggested_filename")
    if suggested_filename:
        defaults["suggested_name"] = Path(suggested_filename).stem

    # Автоподстановка из MRZ (если есть)
    mrz_info = parse_mrz(text)
    if mrz_info:
        if defaults.get("person") in (None, "") and mrz_info.get("person"):
            defaults["person"] = mrz_info["person"]
        for key in ("date_of_birth", "expiration_date", "passport_number"):
            if mrz_info.get(key):
                defaults[key] = mrz_info[key]

    # Если LLM и MRZ не дали владельца, пробуем извлечь из текста документа
    if not (defaults.get("person") or "").strip():
        parsed_person = _parse_person_from_text(text)
        if parsed_person:
            defaults["person"] = parsed_person

    # Единый список тегов без дублей
    tag_values = []
    for key in ("tags", "tags_ru", "tags_en"):
        tag_values.extend(defaults.get(key) or [])
    for key in ("category", "subcategory", "doc_type", "issuer", "person"):
        value = defaults.get(key)
        if value:
            tag_values.append(value)
    defaults["tags"] = list(dict.fromkeys(tag for tag in tag_values if tag))

    metadata_model = Metadata(**defaults)
    return {
        "prompt": result.get("prompt"),
        "raw_response": result.get("raw_response"),
        "metadata": metadata_model,
    }


# Автообнаружение плагинов (не критично, падать не будем)
try:
    from plugins import load_plugins as _load_plugins
    _load_plugins()
except Exception:  # pragma: no cover
    logger.debug("Plugin loading skipped", exc_info=True)
