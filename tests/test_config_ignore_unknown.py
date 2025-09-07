import pytest

pytest.importorskip("dotenv")

from config import Config


def test_ignore_unknown_env_vars(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("UNKNOWN_VAR=1\nLOG_LEVEL=DEBUG\n", encoding="utf-8")

    cfg = Config(_env_file=env_file)

    assert cfg.log_level == "DEBUG"
    assert not hasattr(cfg, "unknown_var")
