from __future__ import annotations

"""Простой модуль для получения эмбеддингов и расчёта сходства."""

import hashlib
import math
from typing import List


def get_embedding(text: str, dimensions: int = 8) -> List[float]:
    """Вернуть детерминированный вектор для *text*.

    Здесь используется простое хеширование, чтобы избежать внешних зависимостей
    при тестировании. В реальной системе вместо этого должен вызываться
    embedding‑API.
    """
    if not text:
        return [0.0] * dimensions
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    step = len(digest) // dimensions
    vec = []
    for i in range(dimensions):
        chunk = digest[i * step:(i + 1) * step]
        vec.append(int.from_bytes(chunk, "big") / 2 ** 32)
    return vec


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
