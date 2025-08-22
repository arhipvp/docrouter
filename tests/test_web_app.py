import os
import sys
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from web_app.server import app  # noqa: E402


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


def test_root_returns_form():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert '<form action="/upload" method="post" enctype="multipart/form-data">' in response.text
