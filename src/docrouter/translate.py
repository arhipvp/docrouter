from .config import settings
import httpx

async def translate_text(text: str, source: str, target: str = "ru") -> str:
    if settings.translate_provider == "deepl" and settings.deepl_api_key:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api-free.deepl.com/v2/translate",
                headers={"Authorization": f"DeepL-Auth-Key {settings.deepl_api_key}"},
                data={"text": text, "source_lang": source.upper(), "target_lang": target.upper()},
            )
            r.raise_for_status()
            return r.json()["translations"][0]["text"]
    return text
