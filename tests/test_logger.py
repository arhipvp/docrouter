import sys
import importlib
import logging
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))


def test_get_logger_rotates(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yml"
    log_file = tmp_path / "app.log"
    cfg.write_text(
        f"""
logging:
  level: INFO
  file: "{log_file}"
  max_bytes: 100
  backup_count: 1
  format: "%(levelname)s:%(message)s"
"""
    )
    monkeypatch.setenv("DOCROUTER_CONFIG", str(cfg))

    root = logging.getLogger()
    root.handlers.clear()

    import logger

    importlib.reload(logger)

    log = logger.get_logger("test")
    for _ in range(20):
        log.info("x" * 10)

    assert log_file.exists()
    assert log_file.with_suffix(".1").exists()
    assert "INFO:xxxxxxxxxx" in log_file.read_text()

    root.handlers.clear()
