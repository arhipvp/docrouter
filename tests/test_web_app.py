import os
import sys
from fastapi.testclient import TestClient

# Добавляем путь к src до импорта сервера
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# In-memory БД для тестов (выставить ДО импорта сервера)
os.environ["DB_URL"] = ":memory:"

# Импортируем сервер
from web_app import server  # noqa: E402

app = server.app


def test_upload_and_retrieve_metadata():
    client = TestClient(app)
    resp = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
        params={"dry_run": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert {"id", "metadata", "path", "status"} <= set(data.keys())

    file_id = data["id"]
    assert data["status"] == "dry_run"
    assert data["metadata"]["extracted_text"].strip() == "content"

    resp2 = client.get(f"/metadata/{file_id}")
    assert resp2.status_code == 200
    assert resp2.json() == data["metadata"]


def test_download_file(tmp_path):
    # Подменяем выходной каталог, чтобы файл реально сохранился в tmp
    server.config.output_dir = str(tmp_path)

    client = TestClient(app)
    resp = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
    )
    assert resp.status_code == 200
    file_id = resp.json()["id"]

    download = client.get(f"/download/{file_id}")
    assert download.status_code == 200
    assert download.content == b"content"


def test_download_file_not_found(tmp_path):
    server.config.output_dir = str(tmp_path)

    client = TestClient(app)
    resp = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
    )
    assert resp.status_code == 200
    file_id = resp.json()["id"]

    # Удаляем физический файл, чтобы провалить скачивание
    record = server.database.get_file(file_id)
    assert record and "path" in record
    path = record["path"]
    if os.path.exists(path):
        os.remove(path)

    resp_missing = client.get(f"/download/{file_id}")
    assert resp_missing.status_code == 404

    # Несуществующий ID
    resp_unknown = client.get("/download/unknown")
    assert resp_unknown.status_code == 404


def test_root_returns_form():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert '<form action="/upload" method="post" enctype="multipart/form-data">' in resp.text
