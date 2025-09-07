import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# Используем in-memory БД
os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import upload  # noqa: E402
from models import Metadata  # noqa: E402

app = server.app


async def _mock_generate_metadata(text, folder_tree=None, folder_index=None):
    return {
        "metadata": Metadata(person="Иван", category="Счета", date="2024-05-01"),
        "prompt": "",
        "raw_response": "",
    }


def test_finalize_file_moves_and_creates_metadata(tmp_path, monkeypatch):
    server.database.init_db()
    server.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload, "UPLOAD_DIR", upload_dir)

    monkeypatch.setattr(server, "extract_text", lambda path, language="eng": "")
    monkeypatch.setattr(
        server.metadata_generation, "generate_metadata", _mock_generate_metadata
    )

    with TestClient(app) as client:
        resp = client.post("/upload", files={"file": ("test.pdf", b"data")})
        assert resp.status_code == 200
        file_id = resp.json()["id"]
        temp_path = Path(resp.json()["path"])
        assert temp_path.exists()

        finalize_resp = client.post(
            f"/files/{file_id}/finalize", json={"confirm": True}
        )
        assert finalize_resp.status_code == 200
        dest_path = Path(finalize_resp.json()["path"])
        record = server.database.get_file(file_id)

    assert dest_path.exists()
    assert not temp_path.exists()
    assert dest_path.with_suffix(dest_path.suffix + ".json").exists()

    assert record is not None
    assert record.status == "processed"
