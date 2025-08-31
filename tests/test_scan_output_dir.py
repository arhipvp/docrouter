import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from web_app import server
from web_app.routes.files import _scan_output_dir


def test_scan_output_dir_updates_on_rename(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    db_path = tmp_path / "db.sqlite"
    monkeypatch.setattr(server.database, "_DB_PATH", db_path)
    server.database.init_db()

    server.config.output_dir = str(out_dir)

    file = out_dir / "doc.txt"
    file.write_text("content")

    _scan_output_dir()
    records = server.database.list_files()
    assert len(records) == 1
    file_id = records[0].id

    new_path = out_dir / "renamed.txt"
    file.rename(new_path)

    _scan_output_dir()
    records = server.database.list_files()
    assert len(records) == 1
    record = records[0]
    assert record.id == file_id
    assert record.path == str(new_path)
