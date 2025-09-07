import os
import sys
from pathlib import Path
import asyncio

from fastapi.testclient import TestClient

# Подключаем исходники
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# Используем in-memory БД
os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import upload as upload_module  # noqa: E402
from models import Metadata  # noqa: E402


async def _mock_generate_metadata(text, folder_tree=None, folder_index=None, file_info=None):
    meta = Metadata(person="John Doe", date="2024-01-01")
    return {"metadata": meta, "prompt": None, "raw_response": None}


def _mock_extract_text(path, language="eng"):
    return path.read_text(encoding="utf-8")


def test_upload_dry_run_keeps_file(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    out_dir = tmp_path / "out"
    (out_dir / "John Doe").mkdir(parents=True)
    server.config.output_dir = str(out_dir)

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload_module, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload_module, "OCR_AVAILABLE", True)

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)

    with TestClient(server.app) as client:
        resp = client.post(
            "/upload",
            params={"dry_run": "true"},
            files={"file": ("doc.txt", b"data")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["missing"] == []

    saved_path = Path(data["path"])
    assert saved_path.parent == upload_dir
    assert saved_path.read_text(encoding="utf-8") == "data"
    assert not Path(data["suggested_path"]).exists()

