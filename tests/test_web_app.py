import os
import sys
from fastapi.testclient import TestClient

# Добавляем путь к src
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# In-memory БД для тестов (должно быть выставлено до импорта сервера)
os.environ["DB_URL"] = ":memory:"

# Импортируем сервер как модуль, чтобы иметь доступ к app и config
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
    # Подменяем выходной каталог, чтобы файл реально сохранился здесь
    server.config.output_dir = str(tmp_path)

    client = TestClient(app)
    response = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
    )
    assert response.status_code == 200
    file_id = response.json()["id"]

    download = client.get(f"/download/{file_id}")
    assert download.status_code == 200
    assert download.content == b"content"


def test_download_file_not_found(tmp_path):
    # Подменяем выходной каталог
    server.config.output_dir = str(tmp_path)

    client = TestClient(app)
    response = client.post(
        "/upload",
        files={"file": ("example.txt", b"content")},
    )
    assert response.status_code == 200
    file_id = response.json()["id"]

    # Достаём путь из БД и удаляем файл, чтобы получить 404
    record = server.database.get_file(file_id)
    assert record and "path" in record
    path = record["path"]
    if os.path.exists(path):
        os.remove(path)

    resp_missing = client.get(f"/download/{file_id}")
    assert resp_missing.status_code == 404

    resp_unknown = client.get("/download/unknown")
    assert resp_unknown.status_code == 404


def test_root_returns_form():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert '<form action="/upload" method="post" enctype="multipart/form-data">' in response.text
