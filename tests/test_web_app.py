import os
import sys
import threading
import time
from pathlib import Path

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

    def patch(self, path, **kwargs):
        return self.session.patch(self.base_url + path, **kwargs)

    def delete(self, path, **kwargs):
        return self.session.delete(self.base_url + path, **kwargs)


def _mock_generate_metadata(text: str, folder_tree=None):
    """Детерминированные метаданные для стабильных проверок."""
    return {
        "prompt": "PROMPT",
        "raw_response": "{\"date\": \"2024-01-01\"}",
        "metadata": {
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
        },
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
        assert {
            "id",
            "filename",
            "metadata",
            "path",
            "status",
            "prompt",
            "raw_response",
            "missing",
        } <= set(data.keys())
        file_id = data["id"]
        assert data["filename"] == "example.txt"
        assert data["status"] in {"dry_run", "processed"}
        assert data["missing"] == []
        assert data["metadata"]["extracted_text"].strip() == "content"
        assert data["metadata"]["language"] == "deu"
        assert captured["language"] == "deu"
        assert data["prompt"] == "PROMPT"
        assert data["raw_response"] == "{\"date\": \"2024-01-01\"}"

        # Чтение метаданных
        meta = client.get(f"/metadata/{file_id}")
        assert meta.status_code == 200
        assert meta.json() == data["metadata"]

        # Скачивание файла
        download = client.get(f"/download/{file_id}")
        assert download.status_code == 200
        assert download.content == b"content"


def test_upload_images_returns_sources(tmp_path, monkeypatch):
    server.database.init_db()

    captured = {}

    def _mock_merge(paths):
        captured["paths"] = [Path(p).name for p in paths]
        tmp_file = tmp_path / "tmp.pdf"
        tmp_file.write_bytes(b"PDF")
        return tmp_file

    def _mock_extract_text(path, language="eng"):
        captured["language"] = language
        return "pdf text"

    monkeypatch.setattr(server, "merge_images_to_pdf", _mock_merge)
    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)

    with LiveClient(app) as client:
        files = [
            ("files", ("b.jpg", b"1", "image/jpeg")),
            ("files", ("a.jpg", b"2", "image/jpeg")),
        ]
        resp = client.post(
            "/upload/images",
            data={"language": "deu"},
            files=files,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == ["a.jpg", "b.jpg"]
        assert data["metadata"]["language"] == "deu"
        assert captured["language"] == "deu"
        file_id = data["id"]

        record = server.database.get_file(file_id)
        assert record and record["sources"] == ["a.jpg", "b.jpg"]
        assert Path(record["path"]).exists()


def test_details_endpoint_returns_full_record(tmp_path, monkeypatch):
    server.database.init_db()

    captured = {}

    def _mock_extract_text(path, language="eng"):
        captured["language"] = language
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)

    with LiveClient(app) as client:
        resp = client.post(
            "/upload",
            data={"language": "deu"},
            files={"file": ("example.txt", b"content")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["missing"] == []
        file_id = data["id"]

        details = client.get(f"/files/{file_id}/details")
        assert details.status_code == 200
        assert details.json() == data


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
        assert 'id="upload-progress"' in resp.text
        assert 'id="ai-exchange"' in resp.text
        assert 'id="folder-tree"' in resp.text


def test_files_endpoint_lists_uploaded_files(tmp_path):
    """После загрузки файл отображается в списке."""
    server.database.init_db()
    server.config.output_dir = str(tmp_path)
    with LiveClient(app) as client:
        resp = client.post("/upload", files={"file": ("example.txt", b"content")})
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        listing = client.get("/files")
        assert listing.status_code == 200
        files = listing.json()
        ids = [item["id"] for item in files]
        assert file_id in ids
        names = [item["filename"] for item in files]
        assert "example.txt" in names

def test_folder_crud_operations(tmp_path):
    server.config.output_dir = str(tmp_path)
    with LiveClient(app) as client:
        resp = client.post("/folders", params={"path": "a/b"})
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "name": "a",
                "path": "a",
                "children": [
                    {"name": "b", "path": "a/b", "children": []}
                ],
            }
        ]

        resp = client.patch("/folders/a/b", params={"new_name": "c"})
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "name": "a",
                "path": "a",
                "children": [
                    {"name": "c", "path": "a/c", "children": []}
                ],
            }
        ]

        resp = client.delete("/folders/a/c")
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "name": "a",
                "path": "a",
                "children": [],
            }
        ]


def test_upload_pending_then_finalize(tmp_path, monkeypatch):
    server.database.init_db()
    server.config.output_dir = str(tmp_path)

    def _mock_extract_text(path, language="eng"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _metadata_pending(text: str, folder_tree=None):
        return {
            "prompt": "PROMPT",
            "raw_response": "{}",
            "metadata": {
                "category": "Финансы",
                "subcategory": "Банки",
                "issuer": "Sparkasse",
                "person": None,
                "doc_type": None,
                "date": "2024-01-01",
                "amount": None,
                "tags": [],
                "suggested_filename": None,
                "description": None,
            },
        }

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _metadata_pending)

    with LiveClient(app) as client:
        resp = client.post("/upload", files={"file": ("doc.txt", b"content")})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["missing"] == [
            "Финансы",
            "Финансы/Банки",
            "Финансы/Банки/Sparkasse",
        ]
        file_id = data["id"]

        resp_folder = client.post("/folders", params={"path": data["missing"][-1]})
        assert resp_folder.status_code == 200

        resp_final = client.post(f"/files/{file_id}/finalize")
        assert resp_final.status_code == 200
        final_data = resp_final.json()
        assert final_data["status"] == "processed"
        assert final_data["missing"] == []
        assert Path(final_data["path"]).exists()


def test_preview_endpoint_serves_file(tmp_path):
    server.database.init_db()
    server.config.output_dir = str(tmp_path)
    with LiveClient(app) as client:
        resp = client.post("/upload", files={"file": ("example.txt", b"content")})
        assert resp.status_code == 200
        file_id = resp.json()["id"]
        prev = client.get(f"/preview/{file_id}")
        assert prev.status_code == 200
        assert prev.headers["content-type"].startswith("text/plain")
        assert prev.text.strip() == "content"

