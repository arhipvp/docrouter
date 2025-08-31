import json
import os
import sys
from pathlib import Path
import asyncio

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from docrouter import process_directory


def test_parse_error_moves_file_and_creates_json(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    bad_file = input_dir / "bad.xyz"
    bad_file.write_text("data", encoding="utf-8")

    dest_root = tmp_path / "Archive"

    # Выполняем обработку, чтобы Unsorted и errors создавались в tmp_path
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        asyncio.run(process_directory(input_dir, dest_root, dry_run=True))
    finally:
        os.chdir(cwd)

    moved = tmp_path / "Unsorted" / "bad.xyz"
    assert moved.exists()

    error_json = tmp_path / "errors" / "bad.xyz.json"
    assert error_json.exists()
    data = json.loads(error_json.read_text(encoding="utf-8"))
    assert "Unsupported/unknown" in data["error"]
