"""
Metadata generation module.

This module provides a high level :func:`generate_metadata` function that can
use either OpenRouter LLM or a local rule-based analyzer.  The abstraction makes
it easy to switch between cloud and local models.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import requests


__all__ = [
    "generate_metadata",
    "MetadataAnalyzer",
    "OpenRouterAnalyzer",
    "RegexAnalyzer",
]


class MetadataAnalyzer(ABC):
    """Abstract base class for metadata analyzers."""

    @abstractmethod
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze *text* and return a metadata dictionary."""


class OpenRouterAnalyzer(MetadataAnalyzer):
    """Analyzer that delegates to an OpenRouter-hosted LLM."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "anthropic/claude-3-haiku-20240307"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY environment variable required")
        self.model = model

    def analyze(self, text: str) -> Dict[str, Any]:
        prompt = (
            "You are an assistant that extracts structured metadata from documents.\n"
            "Return a JSON object with the fields: category, subcategory, issuer, person, doc_type,\n"
            "date, amount, tags (list of strings), suggested_filename, description.\n"
            f"Document text:\n{text}"
        )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/docrouter",
            "X-Title": "DocRouter Metadata Generator",
        }

        response = requests.post(self.API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid JSON from OpenRouter") from exc


class RegexAnalyzer(MetadataAnalyzer):
    """A very small local analyzer based on regular expressions.

    This implementation is intentionally simple and is intended for testing or
    as a fallback when no LLM is available."""

    DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
    AMOUNT_RE = re.compile(r"([0-9]+(?:[.,][0-9]{2})?)")

    def analyze(self, text: str) -> Dict[str, Any]:
        date_match = self.DATE_RE.search(text)
        amount_match = self.AMOUNT_RE.search(text)
        return {
            "category": None,
            "subcategory": None,
            "issuer": None,
            "person": None,
            "doc_type": None,
            "date": date_match.group(1) if date_match else None,
            "amount": amount_match.group(1) if amount_match else None,
            "tags": [],
            "suggested_filename": None,
            "description": None,
        }


def generate_metadata(text: str, analyzer: Optional[MetadataAnalyzer] = None) -> Dict[str, Any]:
    """Generate metadata for *text* using the provided *analyzer*.

    If *analyzer* is ``None`` the function tries to create an
    :class:`OpenRouterAnalyzer`.  When an API key is missing or the
    OpenRouter analyzer cannot be instantiated for any reason, the
    lightweight :class:`RegexAnalyzer` is used as a fallback.

    The returned dictionary always contains the following fields:
    ``category``, ``subcategory``, ``issuer``, ``person``, ``doc_type``,
    ``date``, ``amount``, ``tags``, ``suggested_filename``,
    ``description``.
    """

    if analyzer is None:
        try:
            analyzer = OpenRouterAnalyzer()
        except Exception:
            analyzer = RegexAnalyzer()
    metadata = analyzer.analyze(text)
    defaults = {
        "category": None,
        "subcategory": None,
        "issuer": None,
        "person": None,
        "doc_type": None,
        "date": None,
        "amount": None,
        "tags": [],
        "suggested_filename": None,
        "description": None,
    }
    defaults.update(metadata or {})
    return defaults
