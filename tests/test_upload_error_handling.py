import os
import sys
import logging
from pathlib import Path
import asyncio

import pytest
from fastapi.testclient import TestClient

# Подключаем исходники
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# Используем in-memory БД
os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import upload as upload_module  # noqa: E402

app = server.app


def test_upload_unknown_extension_returns_400(tmp_path, caplog, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path)
    monkeypatch.setattr(upload_module, "OCR_AVAILABLE", True)
    with TestClient(app) as client, caplog.at_level(logging.ERROR):
        resp = client.post("/upload", files={"file": ("bad.xyz", b"data")})
    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("Unsupported/unknown file extension")
    assert "Unsupported/unknown file extension" in caplog.text
