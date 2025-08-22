import os
import sys
import threading
import time
import requests
import uvicorn

# Добавляем путь к src ДО импорта сервера
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Настраиваем окружение ДО импорта сервера
os.environ["DB_URL"] = ":memory:"             # in-memory БД для тестов

# Импортируем сервер
from web_app import server  # noqa: E402

app = server.app


class LiveClient:
    """Простейший HTTP‑клиент поверх запущенного uvicorn."""

    def __init__(self, app, host: str = "127.0.0.1", port: int = 8001):
        self.app = app
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    def __enter__(self):
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="error")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        while not getattr(self.server, "started", False):
            time.sleep(0.01)
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.should_exit = True
        self.thread.join()
        self.session.close()

    def get(self, path, **kwargs):
        return self.session.get(self.base_url + path, **kwargs)

    def post(self, path, **kwargs):
        return self.session.post(self.base_url + path, **kwargs)


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


def test_upload_retrieve_and_download(tmp_path, monkeypatch):
    # Подменяем извлечение текста, метаданные и директорию вывода
    captured = {}

    def _mock_extract_text(path, language="eng"):
        captured["language"] = language
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)

    with LiveClient(app) as client:
        # Загрузка
        resp = client.post(
            "/upload",
            data={"language": "deu"},
            files={"file": ("example.txt", b"content")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert {"id", "metadata", "path", "status"} <= set(data.keys())
        file_id = data["id"]
        assert data["status"] in {"dry_run", "processed"}
        assert data["metadata"]["extracted_text"].strip() == "content"
        assert data["metadata"]["language"] == "deu"
        assert captured["language"] == "deu"

        # Чтение метаданных
        meta = client.get(f"/metadata/{file_id}")
        assert meta.status_code == 200
        assert meta.json() == data["metadata"]

        # Скачивание файла
        download = client.get(f"/download/{file_id}")
        assert download.status_code == 200
        assert download.content == b"content"


def test_download_file_not_found_returns_404(tmp_path):
    server.config.output_dir = str(tmp_path)
    with LiveClient(app) as client:
        # Загружаем корректно
        resp = client.post("/upload", files={"file": ("example.txt", b"content")})
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        # Удаляем физический файл, чтобы получить 404 при скачивании
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


def test_root_returns_form_unprotected():
    """Корневая страница без авторизации доступна и содержит форму."""
    with LiveClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert '<form action="/upload" method="post" enctype="multipart/form-data">' in resp.text
        assert 'name="language"' in resp.text
