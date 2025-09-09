import os
import sys
import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import upload, files  # noqa: E402
from models import Metadata  # noqa: E402

app = server.app


async def _mock_generate_metadata(text, folder_tree=None, folder_index=None):
    return {
        "metadata": Metadata(person="Иван", category="Счета", date="2024-05-01"),
        "prompt": "",
        "raw_response": "",
    }


def test_rerun_ocr_updates_text_and_status(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload, "OCR_AVAILABLE", True)

    monkeypatch.setattr(server, "extract_text", lambda path, language="eng": "old text")
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)

    with TestClient(app) as client:
        resp = client.post("/upload", files={"file": ("test.pdf", b"data")})
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        monkeypatch.setattr(
            files,
            "ocr_pipeline",
            SimpleNamespace(extract_text=lambda path, language, psm: "new text"),
        )
        rerun_resp = client.post(
            f"/files/{file_id}/rerun_ocr", json={"language": "eng", "psm": 3}
        )
        assert rerun_resp.status_code == 200
        assert rerun_resp.json()["extracted_text"] == "new text"

        file_resp = client.get(f"/files/{file_id}")
        assert file_resp.status_code == 200
        data = file_resp.json()
        assert data["metadata"]["extracted_text"] == "new text"
        assert data["status"] == "draft"
