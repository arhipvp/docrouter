import pytest

pytest.importorskip("dotenv")

from config import Config


def test_env_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=DEBUG\nOUTPUT_DIR=FromEnvFile\n", encoding="utf-8")

    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    cfg = Config(_env_file=env_file)

    assert cfg.log_level == "WARNING"
    assert cfg.output_dir == "FromEnvFile"
