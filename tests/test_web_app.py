import io
import os
import sys
import threading
import time
from pathlib import Path
import asyncio

import uvicorn
from PIL import Image
import pytest
import httpx

# Добавляем путь к src ДО импорта сервера
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Настраиваем окружение ДО импорта сервера
os.environ["DB_URL"] = ":memory:"             # in-memory БД для тестов

# Обеспечиваем свежий импорт сервера (другие тесты могут его перезагружать)
sys.modules.pop("web_app.server", None)

# Импортируем сервер
from web_app import server  # noqa: E402
from models import Metadata  # noqa: E402
from config import GENERAL_FOLDER_NAME  # noqa: E402

app = server.app
server.upload.OCR_AVAILABLE = True


class LiveClient:
    """Простейший HTTP-клиент поверх запущенного uvicorn."""

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
        self.session = httpx.Client()
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


async def _mock_generate_metadata(
    text: str,
    folder_tree=None,
    folder_index=None,
    file_info=None,
):
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

    import file_utils, sys
    monkeypatch.setattr("web_app.server.extract_text", _mock_extract_text)
    monkeypatch.setattr("file_utils.extract_text", _mock_extract_text)
    monkeypatch.setattr(
        "metadata_generation.generate_metadata", _mock_generate_metadata
    )
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path)
    (tmp_path / "John Doe").mkdir()
    (tmp_path / "Shared").mkdir()

    with LiveClient(app) as client:
        # Загрузка
        resp = client.post(
            "/upload",
            data={"language": "de"},
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
            "suggested_path",
            "sources",
            "tags_ru",
            "tags_en",
        } <= set(data.keys())
        file_id = data["id"]
        assert data["filename"] == "example.txt"
        assert data["status"] == "draft"
        assert data["missing"] == []
        assert data["metadata"]["extracted_text"].strip() == "content"
        assert data["metadata"]["language"] == "de"
        assert captured["language"] == "deu"
        assert data["prompt"] == "PROMPT"
        assert data["raw_response"] == "{\"date\": \"2024-01-01\"}"
        assert data["metadata"]["person"] == "John Doe"
        assert data["metadata"]["date_of_birth"] == "1990-01-02"
        assert data["metadata"]["expiration_date"] == "2030-01-02"

        monkeypatch.setattr("metadata_generation.generate_metadata", _mock_generate_metadata)
        regen = client.post(f"/files/{file_id}/regenerate")
        assert regen.status_code == 200
        regen_data = regen.json()
        assert "metadata" in regen_data
        assert isinstance(regen_data["missing"], list)
        assert "suggested_path" in regen_data

        # Восстанавливаем ожидаемые метаданные
        server.database.update_file(file_id, metadata=Metadata(**data["metadata"]))

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

        details = client.get(f"/files/{file_id}/details?lang=en")
        assert details.status_code == 200
        assert details.json()["translated_text"] == "content-en"
        assert details.json()["translation_lang"] == "en"

        comment_msg = "Привет"
        monkeypatch.setattr("metadata_generation.generate_metadata", _mock_generate_metadata)
        comment = client.post(
            f"/files/{file_id}/comment", json={"message": comment_msg}
        )
        assert comment.status_code == 200
        comment_data = comment.json()
        assert comment_data["review_comment"] == comment_msg
        assert "suggested_path" in comment_data
        assert isinstance(comment_data["missing"], list)
        assert isinstance(comment_data.get("chat_history"), list)

        # Восстанавливаем метаданные после комментария
        server.database.update_file(file_id, metadata=Metadata(**data["metadata"]))

        details_after = client.get(f"/files/{file_id}/details")
        assert details_after.status_code == 200
        history = details_after.json()["chat_history"]
        assert history and history[-1]["message"] == comment_msg

        translated = client.get(f"/download/{file_id}?lang=en")
        assert translated.status_code == 200
        assert translated.text == "content-en"
        assert calls["n"] == 1

        finalize = client.post(f"/files/{file_id}/finalize", json={"confirm": True})
        assert finalize.status_code == 200
        final_data = finalize.json()
        assert final_data["status"] == "finalized"
        assert final_data["metadata"]["person"] == "John Doe"

        record = server.database.get_file(file_id)
        assert record.person == "John Doe"
        assert record.date_of_birth == "1990-01-02"
        assert record.expiration_date == "2030-01-02"
        assert record.status == "finalized"


def test_translation_error_returns_502(tmp_path, monkeypatch):
    asyncio.run(server.database.run_db(server.database.init_db))

    def _mock_extract_text(path, language="eng"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr("metadata_generation.generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)
    (tmp_path / "John Doe").mkdir()

    with LiveClient(app) as client:
        resp = client.post(
            "/upload",
            data={"language": "de"},
            files={"file": ("example.txt", b"content")},
        )
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        async def _raise_http_error(text, target_lang):
            raise httpx.HTTPError("boom")

        monkeypatch.setattr(server, "translate_text", _raise_http_error)

        translated = client.get(f"/download/{file_id}?lang=en")
        assert translated.status_code == 502
        assert translated.json()["detail"] == "Translation service unavailable"


def test_upload_images_returns_sources(tmp_path, monkeypatch):
    captured = {}

    def _mock_merge(paths):
        captured["paths"] = [Path(p).name for p in paths]
        tmp_file = tmp_path / "tmp.pdf"
        tmp_file.write_bytes(b"PDF")
        return tmp_file

    def _mock_extract_text(path, language="eng"):
        captured["language"] = language
        return "pdf text"

    import file_utils, sys
    monkeypatch.setattr("web_app.server.merge_images_to_pdf", _mock_merge)
    monkeypatch.setattr("file_utils.merge_images_to_pdf", _mock_merge)
    monkeypatch.setattr("web_app.server.extract_text", _mock_extract_text)
    monkeypatch.setattr("file_utils.extract_text", _mock_extract_text)
    monkeypatch.setattr(
        "metadata_generation.generate_metadata", _mock_generate_metadata
    )
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path)
    (tmp_path / "John Doe").mkdir()

    with LiveClient(app) as client:
        files = [
            ("files", ("b.jpg", b"1", "image/jpeg")),
            ("files", ("a.jpg", b"2", "image/jpeg")),
        ]
        resp = client.post(
            "/upload/images",
            data={"language": "de"},
            files=files,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == ["a.jpg", "b.jpg"]
        assert data["metadata"]["language"] == "de"
        assert captured["language"] == "deu"
        file_id = data["id"]

        record = server.database.get_file(file_id)
        assert record and record.sources == ["a.jpg", "b.jpg"]
        assert Path(record.path).exists()


def test_upload_images_download_and_metadata(tmp_path, monkeypatch):
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

    import file_utils, sys
    monkeypatch.setattr("web_app.server.merge_images_to_pdf", _mock_merge)
    monkeypatch.setattr("file_utils.merge_images_to_pdf", _mock_merge)
    monkeypatch.setattr("web_app.server.extract_text", _mock_extract_text)
    monkeypatch.setattr("file_utils.extract_text", _mock_extract_text)
    monkeypatch.setattr(
        server.metadata_generation, "generate_metadata", _mock_generate_metadata
    )
    asyncio.run(server.database.run_db(server.database.init_db))
    server.config.output_dir = str(tmp_path)
    (tmp_path / "John Doe").mkdir()

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
            data={"language": "de"},
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
    asyncio.run(server.database.run_db(server.database.init_db))

    captured = {}

    def _mock_extract_text(path, language="eng"):
        captured["language"] = language
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr("metadata_generation.generate_metadata", _mock_generate_metadata)
    server.config.output_dir = str(tmp_path)
    (tmp_path / "John Doe").mkdir()
    (tmp_path / "Shared").mkdir()

    with LiveClient(app) as client:
        resp = client.post(
            "/upload",
            data={"language": "de"},
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
        expected["review_comment"] = None
        expected["sources"] = None
    assert details_json == expected
