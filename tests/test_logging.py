import logging
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from file_utils import extract_text
from docrouter import process_directory
import metadata_generation


def test_extract_text_logs_error_for_unknown_extension(tmp_path, caplog):
    file_path = tmp_path / "file.xyz"
    file_path.write_text("data", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError):
            extract_text(file_path)
    assert "Unsupported/unknown file extension" in caplog.text


def test_process_directory_logs(tmp_path, monkeypatch, caplog):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    file_path = input_dir / "data.txt"
    file_path.write_text("hello", encoding="utf-8")

    def fake_generate(text):
        return {"date": "2024-01-01"}

    monkeypatch.setattr(metadata_generation, "generate_metadata", fake_generate)

    dest_root = tmp_path / "Archive"

    with caplog.at_level(logging.INFO):
        process_directory(input_dir, dest_root)

    assert f"Processing directory {input_dir}" in caplog.text
    assert f"Processing file {file_path}" in caplog.text
    assert f"Finished processing {file_path}" in caplog.text
