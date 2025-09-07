import sys
import logging
from pathlib import Path

import pytest

# Подключаем исходники
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from file_sorter import place_file  # noqa: E402
from config import GENERAL_FOLDER_NAME  # noqa: E402


def test_place_file_suggests_nested_dirs_and_logs(tmp_path, caplog):
    src = tmp_path / "data.txt"
    src.write_text("hello", encoding="utf-8")
    dest_root = tmp_path / "Archive"
    metadata = {
        "suggested_name": "data",
        "date": "2024-01-01",
        "category": "sub1",
        "subcategory": "sub2",
    }
    with caplog.at_level(logging.DEBUG):
        dest, missing, confirmed = place_file(
            src, metadata, dest_root, dry_run=False
        )
    expected = dest_root / GENERAL_FOLDER_NAME / "sub1" / "sub2" / "2024-01-01__data.txt"
    assert dest == expected
    assert missing == [
        f"{GENERAL_FOLDER_NAME}",
        f"{GENERAL_FOLDER_NAME}/sub1",
        f"{GENERAL_FOLDER_NAME}/sub1/sub2",
    ]
    assert "Missing directories (no create)" in caplog.text
    assert src.exists()
    assert confirmed is False
