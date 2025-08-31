"""Обёртка для вызова OpenRouter."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import httpx

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME,
)


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
