"""Utilities for generating and comparing text embeddings."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import List

import requests

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

logger = logging.getLogger(__name__)


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
FALLBACK_DIM = 50


def _call_openrouter(text: str) -> List[float]:
    """Request embedding from OpenRouter API."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    base = OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
    url = base.rstrip("/") + "/embeddings"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {"model": DEFAULT_EMBEDDING_MODEL, "input": text}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["embedding"]


def _simple_embedding(text: str, dim: int = FALLBACK_DIM) -> List[float]:
    """A deterministic local embedding based on hashing words."""
    vec = [0.0] * dim
    for word in text.lower().split():
        idx = hash(word) % dim
        vec[idx] += 1.0
    return vec


def get_embedding(text: str) -> List[float]:
    """Generate an embedding for *text* using OpenRouter or a local fallback."""
    try:
        return _call_openrouter(text)
    except Exception as exc:  # pragma: no cover - network or config issues
        logger.debug("OpenRouter embedding failed: %s", exc)
        return _simple_embedding(text)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


__all__ = ["get_embedding", "cosine_similarity"]
