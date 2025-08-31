import asyncio
import pytest
from services import openrouter


def test_chat_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(openrouter, "OPENROUTER_API_KEY", "")
    with pytest.raises(openrouter.OpenRouterError):
        asyncio.run(openrouter.chat([{"role": "user", "content": "hi"}]))
