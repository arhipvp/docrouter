from __future__ import annotations

"""Простой модуль для получения эмбеддингов и расчёта сходства."""

import math
from typing import List

from config import config
from services import openrouter


async def get_embedding(text: str, model: str | None = None) -> List[float]:
    """Получить эмбеддинг для текста через сервис OpenRouter."""

    if not text:
        return []

    model_name = model or config.openrouter_model or "text-embedding-3-small"
    return await openrouter.embed(text, model_name)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Косинусное сходство между двумя векторами."""
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


__all__ = ["get_embedding", "cosine_similarity"]
