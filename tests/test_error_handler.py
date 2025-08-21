import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import error_handler


def test_handle_error_moves_file(tmp_path, caplog, monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    test_file = tmp_path / "doc.txt"
    test_file.write_text("content")
    err = ValueError("boom")
    with caplog.at_level("INFO"):
        error_handler.handle_error(test_file, err)
    dest = tmp_path / "Unsorted" / "doc.txt"
    assert dest.exists()
    assert not test_file.exists()
    assert "Moved" in caplog.text


def test_handle_error_dry_run(tmp_path, caplog, monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    test_file = tmp_path / "doc.txt"
    test_file.write_text("content")
    err = ValueError("boom")
    with caplog.at_level("INFO"):
        error_handler.handle_error(test_file, err)
    dest = tmp_path / "Unsorted" / "doc.txt"
    assert not dest.exists()
    assert test_file.exists()
    assert "Dry-run" in caplog.text


def test_is_dry_run_from_config(tmp_path, monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    cfg = tmp_path / "config.yml"
    cfg.write_text("dry_run: true\n")
    monkeypatch.setenv("CONFIG_PATH", str(cfg))
    assert error_handler.is_dry_run() is True
