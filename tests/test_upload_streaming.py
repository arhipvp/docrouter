import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# Используем in-memory БД
os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import upload  # noqa: E402
from models import Metadata  # noqa: E402

app = server.app


async def _mock_generate_metadata(text, folder_tree=None, folder_index=None):
    """Возвращает пустые метаданные для ускорения тестов."""
    return {"metadata": Metadata(), "prompt": "", "raw_response": ""}


def test_large_file_processed_in_chunks(tmp_path, monkeypatch):
    server.database.init_db()
    server.config.output_dir = str(tmp_path)
    monkeypatch.setattr(upload, "UPLOAD_DIR", tmp_path)

    def _mock_extract_text(path, language="eng"):
        return ""

    monkeypatch.setattr(server, "extract_text", _mock_extract_text)
    monkeypatch.setattr(
        server.metadata_generation, "generate_metadata", _mock_generate_metadata
    )

    import starlette.datastructures as sd

    call_sizes: list[int] = []
    original_read = sd.UploadFile.read

    async def tracking_read(self, size: int = -1):
        call_sizes.append(size)
        return await original_read(self, size)

    monkeypatch.setattr(sd.UploadFile, "read", tracking_read)

    big_content = b"x" * (1024 * 1024 * 2 + 12345)  # >2MB
    with TestClient(app) as client:
        resp = client.post("/upload", files={"file": ("big.txt", big_content)})

    assert resp.status_code == 200
    assert -1 not in call_sizes
    assert max(call_sizes) <= 1024 * 1024
    assert len([s for s in call_sizes if s > 0]) > 2

    saved_path = Path(resp.json()["path"])
    assert saved_path.exists()
    assert saved_path.stat().st_size == len(big_content)
