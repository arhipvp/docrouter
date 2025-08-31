import asyncio

import pytest

from file_utils.embeddings import get_embedding
from services.openrouter import embed, OpenRouterError


def test_get_embedding_returns_vector(monkeypatch):
    async def fake_embed(text: str, model: str):
        return [0.1] * 8

    monkeypatch.setattr("file_utils.embeddings.openrouter.embed", fake_embed)

    vec = asyncio.run(get_embedding("hello"))
    assert len(vec) == 8


def test_embed_non_json_response(monkeypatch):
    class DummyResponse:
        status_code = 200
        text = "<html></html>"

        def raise_for_status(self) -> None:
            pass

        def json(self):  # type: ignore[override]
            raise ValueError("no json")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return DummyResponse()

    monkeypatch.setattr("services.openrouter.OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("services.openrouter.httpx.AsyncClient", DummyClient)

    with pytest.raises(OpenRouterError):
        asyncio.run(embed("text", "model"))
