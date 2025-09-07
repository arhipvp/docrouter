import os
import sys
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
from models import Metadata  # noqa: E402


async def _mock_generate_metadata(text, folder_tree=None, folder_index=None, file_info=None):
    return {"metadata": Metadata(), "prompt": None, "raw_response": None}


def _mock_extract_text(path, language="eng"):
    return path.read_text(encoding="utf-8")


def test_upload_path_traversal_is_sanitized(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path / "out")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload_module, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload_module, "OCR_AVAILABLE", True)

    secret = upload_dir / "secret.txt"
    secret.write_text("SECRET", encoding="utf-8")

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)

    with TestClient(server.app) as client:
        resp = client.post("/upload", files={"file": ("../../secret.txt", b"payload")})
    assert resp.status_code == 200
    data = resp.json()
    uploaded_path = Path(data["path"]).resolve()
    assert uploaded_path.parent == upload_dir.resolve()
    assert uploaded_path.name != "secret.txt"
    assert secret.read_text(encoding="utf-8") == "SECRET"
    assert uploaded_path.read_text(encoding="utf-8") == "payload"
