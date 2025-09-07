import os
import sys
from pathlib import Path
import logging

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import chat as chat_route  # noqa: E402
from models import Metadata  # noqa: E402

app = server.app


def test_chat_truncates_context(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(server.database, "_DB_PATH", tmp_path / "test.sqlite")
    server.database.init_db()
    metadata = Metadata(extracted_text="x" * 5000)
    server.database.add_file("123", "file.txt", metadata, path=str(tmp_path))

    captured = {}

    async def fake_chat(messages, **kwargs):
        captured["messages"] = messages
        return "ok", None, None

    monkeypatch.setattr(chat_route.openrouter, "chat", fake_chat)

    with TestClient(app) as client:
        with caplog.at_level(logging.INFO):
            resp = client.post("/chat/123?max_context=1000", json={"message": "hi"})

    server.database.init_db()

    assert resp.status_code == 200
    assert len(captured["messages"][0]["content"]) == 1000
    assert "truncating extracted text" in caplog.text.lower()
