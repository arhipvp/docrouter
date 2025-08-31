import os
import asyncio

os.environ["DB_URL"] = ":memory:"

from web_app import server  # noqa: E402
from web_app.routes import files as files_module  # noqa: E402


def test_list_files_uses_cache(monkeypatch, tmp_path):
    files_module._last_scan_time = 0
    files_module._last_upload_mtime = 0
    server.config.output_dir = str(tmp_path)
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(files_module, "UPLOAD_DIR", upload_dir)

    calls = {"n": 0}

    def fake_scan():
        calls["n"] += 1

    monkeypatch.setattr(files_module, "_scan_output_dir", fake_scan)

    asyncio.run(files_module.list_files())
    asyncio.run(files_module.list_files())

    assert calls["n"] == 1
