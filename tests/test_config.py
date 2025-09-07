import os
from pathlib import Path

from config import Settings


def test_load_from_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    settings = Settings()
    assert settings.log_level == "DEBUG"


def test_env_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    settings = Settings()
    assert settings.log_level == "WARNING"
