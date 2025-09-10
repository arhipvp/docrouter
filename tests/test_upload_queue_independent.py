import os
import sys
from pathlib import Path
import asyncio

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

os.environ["DB_URL"] = ":memory:"

from models import Metadata  # noqa: E402



async def _mock_generate_metadata(text, folder_tree=None, folder_index=None):
    return {
        "metadata": Metadata(person="Иван", category="Счета", date="2024-05-01"),
        "prompt": "",
        "raw_response": "",
    }


def test_two_files_processed_independently(tmp_path, monkeypatch):
    import importlib

    server_mod = importlib.import_module("web_app.server")
    upload_mod = importlib.import_module("web_app.routes.upload")

    asyncio.run(server_mod.database.run_db(server_mod.database.init_db))
    server_mod.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload_mod, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload_mod, "OCR_AVAILABLE", True)

    monkeypatch.setattr(server_mod, "extract_text", lambda path, language="eng": "")
    monkeypatch.setattr(
        server_mod.metadata_generation, "generate_metadata", _mock_generate_metadata
    )

    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000100 00000 n \n"
        b"trailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n147\n%%EOF"
    )

    with TestClient(server_mod.app) as client:
        resp1 = client.post("/upload", files={"file": ("one.pdf", pdf_bytes)})
        resp2 = client.post("/upload", files={"file": ("two.pdf", pdf_bytes)})
        file1 = resp1.json()["id"]
        file2 = resp2.json()["id"]

        comment1 = "note1"
        comment2 = "note2"

        assert client.post(f"/files/{file1}/comment", json={"message": comment1}).status_code == 200
        assert client.post(f"/files/{file1}/regenerate").status_code == 200
        assert (
            client.post(f"/files/{file1}/finalize", json={"confirm": True}).status_code
            == 200
        )

        assert client.post(f"/files/{file2}/comment", json={"message": comment2}).status_code == 200
        assert client.post(f"/files/{file2}/regenerate").status_code == 200
        assert (
            client.post(f"/files/{file2}/finalize", json={"confirm": True}).status_code
            == 200
        )

        data1 = client.get(f"/files/{file1}").json()
        data2 = client.get(f"/files/{file2}").json()

    assert data1["status"] == "finalized"
    assert data2["status"] == "finalized"
    assert data1["review_comment"] == comment1
    assert data2["review_comment"] == comment2

    importlib.reload(server_mod)
    importlib.reload(upload_mod)

