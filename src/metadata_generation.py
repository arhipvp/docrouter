"""
Metadata generation module.

This module предоставляет высокоуровневую функцию :func:`generate_metadata`,
которая использует LLM через OpenRouter. При необходимости можно подключить
иные анализаторы.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Callable

import httpx

from models import Metadata

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
        self, text: str, folder_tree: Optional[Dict[str, Any]] = None
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
        self, text: str, folder_tree: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        tree_json = json.dumps(folder_tree or {}, ensure_ascii=False)
        prompt = (
            "You are an assistant that extracts structured metadata from documents.\n"
            "Existing folder tree (JSON):\n"
            f"{tree_json}\n"
            "Если ни одна папка не подходит, предложи новую category/subcategory.\n"
            "Return a JSON object with the fields: category, subcategory, needs_new_folder (boolean), issuer, person, doc_type,\n"
            "date, amount, tags_ru (list of strings), tags_en (list of strings), suggested_filename, description.\n"
            "Suggested_filename must not start or end with a date (YYYY-MM-DD); provide the date only in the 'date' field.\n"
            f"Document text:\n{text}"
        )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "extra_body": {"response_format": {"type": "json_object"}},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
        }

        logger.debug("OpenRouter payload: %s", payload)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
            logger.debug(
                "OpenRouter response status %s: %s", response.status_code, response.text
            )
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
        content = response.json()["choices"][0]["message"]["content"]
        if not content.strip():
            logger.error("Empty content from OpenRouter: %s", response.text)
            raise OpenRouterError("Empty response from OpenRouter")
        if content.strip().startswith("```"):
            content = "\n".join(content.strip().split("\n")[1:-1])
        try:
            metadata = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("JSON decode error from OpenRouter: %s", response.text)
            raise OpenRouterError("Invalid JSON from OpenRouter") from exc
        return {"prompt": prompt, "raw_response": content, "metadata": metadata}


async def generate_metadata(
    text: str,
    analyzer: Optional[MetadataAnalyzer] = None,
    *,
    folder_tree: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate metadata for *text* using the provided *analyzer*.

    If *analyzer* is ``None`` the function creates an :class:`OpenRouterAnalyzer`.
    Любые ошибки при обращении к OpenRouter пробрасываются вызывающему коду.

    The returned dictionary always contains the following fields:
    ``category``, ``subcategory``, ``issuer``, ``person``, ``doc_type``,
    ``date``, ``amount``, ``tags``, ``tags_ru``, ``tags_en``,
    ``suggested_filename``, ``description``, ``needs_new_folder``.
    """

    if analyzer is None:
        analyzer = OpenRouterAnalyzer()
    result = await analyzer.analyze(text, folder_tree=folder_tree)
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
        "tags": [],
        "tags_ru": [],
        "tags_en": [],
        "suggested_filename": None,
        "description": None,
        "needs_new_folder": False,
    }
    defaults.update(metadata or {})

    suggested_filename = defaults.get("suggested_filename")
    if suggested_filename:
        defaults["suggested_name"] = Path(suggested_filename).stem

    mrz_info = parse_mrz(text)
    if mrz_info:
        if defaults.get("person") in (None, "") and mrz_info.get("person"):
            defaults["person"] = mrz_info["person"]
        for key in ("date_of_birth", "expiration_date", "passport_number"):
            if mrz_info.get(key):
                defaults[key] = mrz_info[key]
    metadata_model = Metadata(**defaults)
    return {
        "prompt": result.get("prompt"),
        "raw_response": result.get("raw_response"),
        "metadata": metadata_model,
    }


try:  # Автообнаружение плагинов
    from plugins import load_plugins as _load_plugins

    _load_plugins()
except Exception:  # pragma: no cover - отсутствие плагинов не критично
    logger.debug("Plugin loading skipped", exc_info=True)
