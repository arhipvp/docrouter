import os
import sys
import tempfile
from fastapi.testclient import TestClient

# Добавляем путь к src ДО импорта сервера
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Настраиваем окружение ДО импорта сервера
os.environ["DB_URL"] = ":memory:"             # in-memory БД для тестов
os.environ["DOCROUTER_USER"] = "user"         # Basic Auth логин
os.environ["DOCROUTER_PASS"] = "pass"         # Basic Auth пароль

# Импортируем сервер
from web_app import server  # noqa: E402

app = server.app


def _mock_generate_metadata(text: str):
    """Детерминированные метаданные для стабильных проверок."""
    return {
        "category": None,
        "subcategory": None,
        "issuer": None,
        "person": None,
        "doc_type": None,
        "date": "2024-01-01",
        "amount": None,
        "tags": [],
        "suggested_filename": None,
        "description": None,
    }


def test_upload_retrieve_and_download_auth_ok(tmp_path, monkeypatch):
    # Подменяем метаданные и директорию вывода
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)

    client = TestClient(app)

    # Загрузка (защищено Basic Auth)
    resp = client.post("/upload", files={"file": ("example.txt", b"content")}, auth=("user", "pass"))
    assert resp.status_code == 200
    data = resp.json()
    assert {"id", "metadata", "path", "status"} <= set(data.keys())
    file_id = data["id"]
    assert data["status"] in {"dry_run", "processed"}
    assert data["metadata"]["extracted_text"].strip() == "content"

    # Чтение метаданных (защищено Basic Auth)
    meta = client.get(f"/metadata/{file_id}", auth=("user", "pass"))
    assert meta.status_code == 200
    assert meta.json() == data["metadata"]

    # Скачивание файла (защищено Basic Auth)
    download = client.get(f"/download/{file_id}", auth=("user", "pass"))
    assert download.status_code == 200
    assert download.content == b"content"


def test_invalid_credentials_and_no_auth(tmp_path):
    server.config.output_dir = str(tmp_path)
    client = TestClient(app)

    # Неверный пароль
    resp_bad = client.post("/upload", files={"file": ("example.txt", b"content")}, auth=("user", "wrong"))
    assert resp_bad.status_code == 401

    # Без авторизации
    resp_noauth = client.post("/upload", files={"file": ("example.txt", b"content")})
    assert resp_noauth.status_code == 401


def test_download_file_not_found_returns_404(tmp_path):
    server.config.output_dir = str(tmp_path)
    client = TestClient(app)

    # Загружаем корректно
    resp = client.post("/upload", files={"file": ("example.txt", b"content")}, auth=("user", "pass"))
    assert resp.status_code == 200
    file_id = resp.json()["id"]

    # Удаляем физический файл, чтобы получить 404 при скачивании
    record = server.database.get_file(file_id)
    assert record and "path" in record
    path = record["path"]
    if os.path.exists(path):
        os.remove(path)

    resp_missing = client.get(f"/download/{file_id}", auth=("user", "pass"))
    assert resp_missing.status_code == 404

    # Несуществующий ID
    resp_unknown = client.get("/download/unknown", auth=("user", "pass"))
    assert resp_unknown.status_code == 404


def test_root_returns_form_unprotected():
    """Корневая страница без авторизации доступна и содержит форму."""
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert '<form action="/upload" method="post" enctype="multipart/form-data">' in resp.text
