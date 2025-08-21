import httpx
from .config import settings

async def complete(prompt: str, max_tokens: int = 800) -> str:
    if not settings.openrouter_api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}","Content-Type": "application/json"}
    payload = {"model": settings.openrouter_model, "messages": [{"role":"user","content": prompt}], "max_tokens": max_tokens, "temperature": 0}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload); r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
