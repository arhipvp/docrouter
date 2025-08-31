"""Обёртка для вызова OpenRouter."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
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


class OpenRouterError(RuntimeError):
    """Исключение при обращении к OpenRouter."""


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
        try:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenRouter request failed: %s", exc)
            raise OpenRouterError(
                f"OpenRouter request failed: {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("HTTP error during chat request: %s", exc)
            raise OpenRouterError("HTTP error during chat request") from exc
        except ValueError as exc:
            logger.error(
                "OpenRouter returned non-JSON response: %s", response.text
            )
            raise OpenRouterError("OpenRouter returned non-JSON response") from exc

    reply = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    tokens = usage.get("total_tokens")
    cost = usage.get("total_cost")
    return reply, tokens, cost


__all__ = ["chat", "OpenRouterError"]
