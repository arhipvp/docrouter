import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import config_loader


def test_load_config_merges_sources(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yml"
    cfg.write_text("foo: bar\n")
    env = tmp_path / ".env"
    env.write_text("foo=from_env\nbaz=qux\n")
    monkeypatch.setenv("CONFIG_PATH", str(cfg))
    config_loader.load_config.cache_clear()
    assert config_loader.load_config() == {"foo": "from_env", "baz": "qux"}


def test_load_config_caching(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yml"
    cfg.write_text("foo: bar\n")
    env = tmp_path / ".env"
    env.write_text("baz=qux\n")
    monkeypatch.setenv("CONFIG_PATH", str(cfg))
    config_loader.load_config.cache_clear()
    first = config_loader.load_config()
    cfg.write_text("foo: changed\n")
    env.write_text("baz=changed\n")
    second = config_loader.load_config()
    assert second == first
