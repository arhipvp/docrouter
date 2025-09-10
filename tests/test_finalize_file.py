import os
import sys
from pathlib import Path
import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# Используем in-memory БД
os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import upload  # noqa: E402
from models import Metadata  # noqa: E402
from file_sorter import place_file  # noqa: E402

app = server.app


async def _mock_generate_metadata(text, folder_tree=None, folder_index=None):
    return {
        "metadata": Metadata(person="Иван", category="Счета", date="2024-05-01"),
        "prompt": "",
        "raw_response": "",
    }


def test_finalize_file_moves_and_creates_metadata(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload, "OCR_AVAILABLE", True)

    monkeypatch.setattr(server, "extract_text", lambda path, language="eng": "")
    monkeypatch.setattr(
        server.metadata_generation, "generate_metadata", _mock_generate_metadata
    )

    with TestClient(app) as client:
        resp = client.post("/upload", files={"file": ("test.pdf", b"data")})
        assert resp.status_code == 200
        upload_data = resp.json()
        assert upload_data["status"] == "draft"
        file_id = upload_data["id"]
        temp_path = Path(upload_data["path"])
        assert temp_path.exists()

        regen_resp = client.post(f"/files/{file_id}/regenerate")
        assert regen_resp.status_code == 200
        regen_data = regen_resp.json()
        assert regen_data["metadata"]["person"] == "Иван"
        assert regen_data["prompt"] == ""
        assert regen_data["raw_response"] == ""
        assert isinstance(regen_data["missing"], list)
        assert isinstance(regen_data.get("suggested_path"), str)

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
    assert record.status == "finalized"


def test_finalize_pending_file_creates_dirs(tmp_path):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    src = upload_dir / "pending.pdf"
    src.write_bytes(b"data")

    metadata = Metadata(
        person="Иван",
        category="Счета",
        subcategory="Интернет",
        date="2024-05-01",
        needs_new_folder=True,
    )
    meta_dict = metadata.model_dump()
    dest_path, missing, _ = place_file(
        src, meta_dict, server.config.output_dir, dry_run=True, needs_new_folder=True
    )
    metadata = Metadata(**meta_dict)
    file_id = str(uuid.uuid4())
    asyncio.run(
        server.database.run_db(
            server.database.add_file,
            file_id,
            src.name,
            metadata,
            str(src),
            "pending",
            missing=missing,
            suggested_path=str(dest_path),
        )
    )

    with TestClient(app) as client:
        get_resp = client.get(f"/files/{file_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["status"] == "pending"
        assert data["missing"] == missing

        preview_resp = client.post(
            f"/files/{file_id}/finalize", json={"confirm": False}
        )
        assert preview_resp.status_code == 200
        assert preview_resp.json()["missing"] == missing

        finalize_resp = client.post(
            f"/files/{file_id}/finalize", json={"confirm": True}
        )
        assert finalize_resp.status_code == 200
        final_data = finalize_resp.json()
        new_path = Path(final_data["path"])
        record = server.database.get_file(file_id)

    assert new_path.exists()
    assert not src.exists()
    for rel in missing:
        assert (Path(server.config.output_dir) / rel).exists()
    assert record.status == "finalized"


def test_comment_persists_after_finalize(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload, "OCR_AVAILABLE", True)

    monkeypatch.setattr(server, "extract_text", lambda path, language="eng": "")
    monkeypatch.setattr(
        server.metadata_generation, "generate_metadata", _mock_generate_metadata
    )

    with TestClient(app) as client:
        resp = client.post("/upload", files={"file": ("test.pdf", b"data")})
        assert resp.status_code == 200
        upload_data = resp.json()
        assert upload_data["status"] == "draft"
        file_id = upload_data["id"]

        comment_msg = "Важно"
        comment_resp = client.post(
            f"/files/{file_id}/comment", json={"message": comment_msg}
        )
        assert comment_resp.status_code == 200

        finalize_resp = client.post(
            f"/files/{file_id}/finalize", json={"confirm": True}
        )
        assert finalize_resp.status_code == 200

        file_resp = client.get(f"/files/{file_id}")
        assert file_resp.status_code == 200
        data = file_resp.json()
        assert data["chat_history"][-1]["message"] == comment_msg
        assert data["review_comment"] == comment_msg


def test_delete_draft_file_removes_temp_and_json(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload, "OCR_AVAILABLE", True)

    monkeypatch.setattr(server, "extract_text", lambda path, language="eng": "")
    monkeypatch.setattr(
        server.metadata_generation, "generate_metadata", _mock_generate_metadata
    )

    with TestClient(app) as client:
        resp = client.post("/upload", files={"file": ("test.pdf", b"data")})
        assert resp.status_code == 200
        upload_data = resp.json()
        file_id = upload_data["id"]
        temp_path = Path(upload_data["path"])
        json_path = temp_path.with_suffix(temp_path.suffix + ".json")
        json_path.write_text("{}", encoding="utf-8")
        assert temp_path.exists() and json_path.exists()

        del_resp = client.delete(f"/files/{file_id}")
        assert del_resp.status_code == 200
        file_resp = client.get(f"/files/{file_id}")
        assert file_resp.status_code == 404

    assert not temp_path.exists()
    assert not json_path.exists()


def test_delete_file(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path / "archive")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(upload, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(upload, "OCR_AVAILABLE", True)

    monkeypatch.setattr(server, "extract_text", lambda path, language="eng": "")
    monkeypatch.setattr(
        server.metadata_generation, "generate_metadata", _mock_generate_metadata
    )

    with TestClient(app) as client:
        resp = client.post("/upload", files={"file": ("test.pdf", b"data")})
        assert resp.status_code == 200
        upload_data = resp.json()
        file_id = upload_data["id"]

        finalize_resp = client.post(
            f"/files/{file_id}/finalize", json={"confirm": True}
        )
        assert finalize_resp.status_code == 200
        dest_path = Path(finalize_resp.json()["path"])
        meta_path = dest_path.with_suffix(dest_path.suffix + ".json")
        assert dest_path.exists() and meta_path.exists()

        del_resp = client.delete(f"/files/{file_id}")
        assert del_resp.status_code == 200
        file_resp = client.get(f"/files/{file_id}")
        assert file_resp.status_code == 404
        db_record = server.database.get_file(file_id)

    assert db_record is None
    assert not dest_path.exists()
    assert not meta_path.exists()
