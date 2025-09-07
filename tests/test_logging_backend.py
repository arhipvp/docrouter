import logging

import pytest

from file_utils import extract_text, UnsupportedFileType
from file_sorter import place_file


def test_extract_text_logs_error_for_unknown_extension(tmp_path, caplog):
    file_path = tmp_path / "file.xyz"
    file_path.write_text("data", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        with pytest.raises(UnsupportedFileType):
            extract_text(file_path)
    assert "Unsupported/unknown file extension" in caplog.text


def test_place_file_logs(tmp_path, caplog):
    src = tmp_path / "doc.txt"
    src.write_text("content", encoding="utf-8")
    metadata = {"date": "2024-01-01", "suggested_name": "doc"}
    dest_root = tmp_path / "Archive"

    with caplog.at_level(logging.INFO):
        place_file(src, metadata, dest_root, dry_run=True)
    assert "Would move" in caplog.text

    src2 = tmp_path / "doc2.txt"
    src2.write_text("content", encoding="utf-8")
    caplog.clear()
    with caplog.at_level(logging.INFO):
        place_file(
            src2,
            metadata,
            tmp_path / "Archive2",
            dry_run=False,
            needs_new_folder=True,
            confirm_callback=lambda _: True,
        )
    assert "Moved" in caplog.text
