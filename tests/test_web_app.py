import io
import os
import sys
import threading
import time
from pathlib import Path

import requests
import uvicorn
from PIL import Image
import pytest

# Добавляем путь к src ДО импорта сервера
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Настраиваем окружение ДО импорта сервера
os.environ["DB_URL"] = ":memory:"             # in-memory БД для тестов

# Импортируем сервер
from web_app import server  # noqa: E402
from models import Metadata  # noqa: E402

app = server.app


@pytest.fixture(autouse=True)
def _mock_embeddings(monkeypatch):
    async def fake_embed(text: str, model: str):
        return [0.1] * 8

    monkeypatch.setattr("file_utils.embeddings.openrouter.embed", fake_embed)


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


async def _mock_generate_metadata(text: str, folder_tree=None):
    """Детерминированные метаданные для стабильных проверок."""
    meta = Metadata(
        person="John Doe",
        date_of_birth="1990-01-02",
        expiration_date="2030-01-02",
        passport_number="X1234567",
        date="2024-01-01",
    )
    return {
        "prompt": "PROMPT",
        "raw_response": "{\"date\": \"2024-01-01\"}",
        "metadata": meta,
    }


def test_index_contains_edit_modal_and_buttons():
    with LiveClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        assert 'id="edit-modal"' in html
        assert 'id="rotate-left-btn"' in html
        assert 'id="rotate-right-btn"' in html
        assert 'id="save-btn"' in html


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
        assert data["metadata"]["person"] == "John Doe"
        assert data["metadata"]["date_of_birth"] == "1990-01-02"
        assert data["metadata"]["expiration_date"] == "2030-01-02"

        # Чтение метаданных
        meta = client.get(f"/metadata/{file_id}")
        assert meta.status_code == 200
        assert meta.json() == data["metadata"]

        # Скачивание файла
        download = client.get(f"/download/{file_id}")
        assert download.status_code == 200
        assert download.content == b"content"

        # Перевод и повторное скачивание
        calls = {"n": 0}

        async def _mock_translate(text, target_lang):
            calls["n"] += 1
            return f"{text}-{target_lang}"

        monkeypatch.setattr(server, "translate_text", _mock_translate)

        details = client.get(f"/files/{file_id}/details?lang=eng")
        assert details.status_code == 200
        assert details.json()["translated_text"] == "content-eng"
        assert details.json()["translation_lang"] == "eng"

        translated = client.get(f"/download/{file_id}?lang=eng")
        assert translated.status_code == 200
        assert translated.text == "content-eng"
        assert calls["n"] == 1

        record = server.database.get_file(file_id)
        assert record.person == "John Doe"
        assert record.date_of_birth == "1990-01-02"
        assert record.expiration_date == "2030-01-02"


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
        assert record and record.sources == ["a.jpg", "b.jpg"]
        assert Path(record.path).exists()


def test_upload_images_download_and_metadata(tmp_path, monkeypatch):
    server.database.init_db()

    captured = {}

    pdf_bytes = b"PDF"

    def _mock_merge(paths):
        captured["paths"] = [Path(p).name for p in paths]
        tmp_file = tmp_path / "tmp.pdf"
        tmp_file.write_bytes(pdf_bytes)
        return tmp_file

    def _mock_extract_text(path, language="eng"):
        captured["language"] = language
        return "page1\npage2"

    monkeypatch.setattr(server, "merge_images_to_pdf", _mock_merge)
    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)

    img1 = io.BytesIO()
    Image.new("RGB", (1, 1), color="red").save(img1, format="JPEG")
    img2 = io.BytesIO()
    Image.new("RGB", (1, 1), color="blue").save(img2, format="JPEG")

    with LiveClient(app) as client:
        files = [
            ("files", ("b.jpg", img1.getvalue(), "image/jpeg")),
            ("files", ("a.jpg", img2.getvalue(), "image/jpeg")),
        ]
        resp = client.post(
            "/upload/images",
            data={"language": "deu"},
            files=files,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"].endswith(".pdf")
        assert data["sources"] == ["a.jpg", "b.jpg"]
        assert data["metadata"]["extracted_text"] == "page1\npage2"

        file_id = data["id"]

        download = client.get(f"/download/{file_id}")
        assert download.status_code == 200
        assert download.content == pdf_bytes

        meta = client.get(f"/metadata/{file_id}")
        assert meta.status_code == 200
        assert meta.json()["extracted_text"] == "page1\npage2"


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

        # merged expectation: есть и поля перевода, и чат-история
        details_json = details.json()
        assert "embedding" in details_json
        expected = data.copy()
        expected["translated_text"] = None
        expected["translation_lang"] = None
        expected["chat_history"] = []
        expected["person"] = data["metadata"]["person"]
        expected["date_of_birth"] = data["metadata"]["date_of_birth"]
        expected["expiration_date"] = data["metadata"]["expiration_date"]
        expected["passport_number"] = data["metadata"]["passport_number"]
        expected["confirmed"] = False
        expected["created_path"] = None
        details_json_no_emb = details_json.copy()
        details_json_no_emb.pop("embedding", None)
        assert details_json_no_emb == expected


def test_download_file_not_found_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)
    with LiveClient(app) as client:
        # Загружаем корректно
        resp = client.post("/upload", files={"file": ("example.txt", b"content")})
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        # Удаляем физический файл, чтобы получить 404 при скачивании
        record = server.database.get_file(file_id)
        assert record and record.path
        path = record.path
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


def test_files_endpoint_lists_uploaded_files(tmp_path, monkeypatch):
    """После загрузки файл отображается в списке."""
    server.database.init_db()
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
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

    async def _metadata_pending(text: str, folder_tree=None):
        meta = Metadata(
            category="Финансы",
            subcategory="Банки",
            issuer="Sparkasse",
            date="2024-01-01",
        )
        return {
            "prompt": "PROMPT",
            "raw_response": "{}",
            "metadata": meta,
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


def test_preview_endpoint_serves_file(tmp_path, monkeypatch):
    server.database.init_db()
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)
    with LiveClient(app) as client:
        resp = client.post("/upload", files={"file": ("example.txt", b"content")})
        assert resp.status_code == 200
        file_id = resp.json()["id"]
        prev = client.get(f"/preview/{file_id}")
        assert prev.status_code == 200
        assert prev.headers["content-type"].startswith("text/plain")
        assert prev.text.strip() == "content"


def test_chat_history(tmp_path, monkeypatch):
    server.database.init_db()
    server.config.output_dir = str(tmp_path)

    def _mock_extract_text(path, language="eng"):
        return "content"

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(server.metadata_generation, "generate_metadata", _mock_generate_metadata)

    async def _mock_chat(messages):
        return "Ответ", 10, 0.02

    monkeypatch.setattr(server.chat.openrouter, "chat", _mock_chat)

    with LiveClient(app) as client:
        resp = client.post(
            "/upload",
            files={"file": ("chat.txt", b"content")},
        )
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        chat1 = client.post(f"/chat/{file_id}", json={"message": "привет"})
        assert chat1.status_code == 200
        data1 = chat1.json()
        assert any(msg["message"] == "привет" for msg in data1["chat_history"])
        assert data1["chat_history"][-1]["tokens"] == 10
        assert data1["chat_history"][-1]["cost"] == 0.02
        assert len(data1["chat_history"]) == 2

        chat2 = client.post(f"/chat/{file_id}", json={"message": "как дела"})
        data2 = chat2.json()
        assert len(data2["chat_history"]) == 4
        assert data2["chat_history"][0]["message"] == "привет"
        assert data2["chat_history"][-1]["tokens"] == 10

        details = client.get(f"/files/{file_id}/details")
        assert details.status_code == 200
        assert len(details.json()["chat_history"]) == 4
