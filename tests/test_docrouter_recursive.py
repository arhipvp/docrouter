import sys
from pathlib import Path
import asyncio

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from docrouter import process_directory
import metadata_generation
from models import Metadata
from config import GENERAL_FOLDER_NAME
from web_app import db as database


def test_process_directory_preserves_subdirs(tmp_path, monkeypatch):
    input_dir = tmp_path / "input" / "sub1" / "sub2"
    input_dir.mkdir(parents=True)
    file_path = input_dir / "data.txt"
    file_path.write_text("hello", encoding="utf-8")

    async def fake_generate(text):
        return {"prompt": None, "raw_response": None, "metadata": Metadata(date="2024-01-01")}

    monkeypatch.setattr(metadata_generation, "generate_metadata", fake_generate)

    dest_root = tmp_path / "Archive"
    database.init_db()
    asyncio.run(process_directory(tmp_path / "input", dest_root))

    expected = dest_root / GENERAL_FOLDER_NAME / "sub1" / "sub2" / "2024-01-01__data.txt"
    assert not expected.exists()
    assert file_path.exists()
    records = database.list_files()
    assert len(records) == 1
    rec = records[0]
    assert rec.status == "pending"
    assert rec.suggested_path == str(expected)
