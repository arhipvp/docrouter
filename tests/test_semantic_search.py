import os
import sys
import asyncio
from pathlib import Path

import pytest

# Подготовка путей
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from web_app import server  # noqa: E402
from file_utils.embeddings import get_embedding  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from models import Metadata  # noqa: E402


def test_semantic_search_returns_similar_document(tmp_path, monkeypatch):
    server.database.init_db()
    server.config.output_dir = str(tmp_path)

    async def fake_embed(text: str, model: str):
        return [float(len(text) + i) for i in range(8)]

    monkeypatch.setattr("file_utils.embeddings.openrouter.embed", fake_embed)

    text = "hello world"
    emb = asyncio.run(get_embedding(text))
    assert len(emb) == 8
    server.database.add_file(
        "1",
        "file1.txt",
        Metadata(extracted_text=text),
        str(tmp_path / "file1.txt"),
        "processed",
        embedding=emb,
    )

    client = TestClient(server.app)
    resp = client.get("/search/semantic", params={"q": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"]
    assert data["results"][0]["id"] == "1"
    assert data["results"][0]["score"] > 0
