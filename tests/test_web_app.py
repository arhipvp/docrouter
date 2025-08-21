import os
import sys
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from web_app.main import app  # noqa: E402


def test_upload_and_retrieve_metadata():
    client = TestClient(app)
    response = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
        params={"dry_run": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert set(["file_id", "metadata", "path", "status"]).issubset(data.keys())
    file_id = data["file_id"]
    assert data["status"] == "dry_run"

    response2 = client.get(f"/files/{file_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["metadata"] == data["metadata"]
    assert data2["status"] == "dry_run"
