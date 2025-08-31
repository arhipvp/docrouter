"""Обёртка для вызова OpenRouter."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import asyncio
import logging

import httpx

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME,
)


logger = logging.getLogger(__name__)


async def chat(messages: List[Dict[str, str]]) -> Tuple[str, int | None, float | None]:
    """Отправить запрос в OpenRouter и вернуть ответ, количество токенов и стоимость."""

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable required")

    model = OPENROUTER_MODEL or "openai/chatgpt-4o-mini"
    base_url = OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
    api_url = base_url.rstrip("/") + "/chat/completions"

    payload: Dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.1}
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": OPENROUTER_SITE_URL or "https://github.com/docrouter",
        "X-Title": OPENROUTER_SITE_NAME or "DocRouter",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(api_url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()

    reply = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    tokens = usage.get("total_tokens")
    cost = usage.get("total_cost")
    return reply, tokens, cost


async def embed(text: str, model: str) -> List[float]:
    """Получить эмбеддинг для текста через OpenRouter.

    Делает несколько попыток при временных ошибках и логирует их."""

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable required")

    base_url = OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
    api_url = base_url.rstrip("/") + "/embeddings"

    payload: Dict[str, Any] = {"model": model, "input": text}
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": OPENROUTER_SITE_URL or "https://github.com/docrouter",
        "X-Title": OPENROUTER_SITE_NAME or "DocRouter",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                response = await client.post(api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429 and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(
                        "OpenRouter rate limited (429). Retrying in %s seconds", wait
                    )
                    await asyncio.sleep(wait)
                    continue
                logger.error("OpenRouter embedding failed: %s", exc)
                raise
            except httpx.HTTPError as exc:
                logger.error("HTTP error during embedding request: %s", exc)
                raise

    raise RuntimeError("Failed to fetch embedding from OpenRouter")
