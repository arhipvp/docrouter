import os
import sys
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from web_app import server  # noqa: E402

app = server.app


def test_upload_and_retrieve_metadata():
    client = TestClient(app)
    response = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
        params={"dry_run": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert set(["id", "metadata", "path", "status"]).issubset(data.keys())
    file_id = data["id"]
    assert data["status"] == "dry_run"
    assert data["metadata"]["extracted_text"].strip() == "content"

    response2 = client.get(f"/metadata/{file_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2 == data["metadata"]


def test_download_file(tmp_path):
    server.METADATA_STORE.clear()
    server.config.output_dir = str(tmp_path)
    client = TestClient(app)
    response = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
    )
    file_id = response.json()["id"]
    download = client.get(f"/download/{file_id}")
    assert download.status_code == 200
    assert download.content == b"content"


def test_download_file_not_found(tmp_path):
    server.METADATA_STORE.clear()
    server.config.output_dir = str(tmp_path)
    client = TestClient(app)
    response = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
    )
    file_id = response.json()["id"]
    # remove file to trigger missing file 404
    path = server.METADATA_STORE[file_id]["path"]
    os.remove(path)
    resp_missing = client.get(f"/download/{file_id}")
    assert resp_missing.status_code == 404
    resp_unknown = client.get("/download/unknown")
    assert resp_unknown.status_code == 404
