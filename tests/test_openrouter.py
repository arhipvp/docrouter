import asyncio
import json
import pytest
import httpx

from services import openrouter


def test_chat_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(openrouter, "OPENROUTER_API_KEY", "")
    with pytest.raises(openrouter.OpenRouterError):
        asyncio.run(openrouter.chat([{"role": "user", "content": "hi"}]))


class DummyAsyncClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def post(self, *args, **kwargs):
        resp = self.responses[self.calls]
        self.calls += 1
        return resp


async def _dummy_sleep(_):
    pass


def test_chat_retries_on_transient_error(monkeypatch):
    req = httpx.Request("POST", "https://openrouter.test")
    failure = httpx.Response(status_code=500, request=req)
    success_data = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
    success = httpx.Response(
        status_code=200, request=req, content=json.dumps(success_data).encode()
    )
    client = DummyAsyncClient([failure, success])

    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda *a, **kw: client)
    monkeypatch.setattr(openrouter.asyncio, "sleep", _dummy_sleep)

    reply, tokens, cost = asyncio.run(
        openrouter.chat([{"role": "user", "content": "hi"}], api_key="key")
    )
    assert reply == "ok"
    assert client.calls == 2
    assert tokens is None and cost is None


def test_chat_exhausts_retries(monkeypatch):
    req = httpx.Request("POST", "https://openrouter.test")
    failure = httpx.Response(status_code=502, request=req)
    client = DummyAsyncClient([failure, failure, failure])

    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda *a, **kw: client)
    monkeypatch.setattr(openrouter.asyncio, "sleep", _dummy_sleep)

    with pytest.raises(openrouter.OpenRouterError) as exc:
        asyncio.run(
            openrouter.chat([{"role": "user", "content": "hi"}], api_key="key")
        )
    assert "3 attempts" in str(exc.value)
    assert client.calls == 3
