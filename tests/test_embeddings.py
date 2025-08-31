import asyncio

from file_utils.embeddings import get_embedding


def test_get_embedding_returns_vector(monkeypatch):
    async def fake_embed(text: str, model: str):
        return [0.1] * 8

    monkeypatch.setattr("file_utils.embeddings.openrouter.embed", fake_embed)

    vec = asyncio.run(get_embedding("hello"))
    assert len(vec) == 8
