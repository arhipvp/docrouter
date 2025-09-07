import importlib
import sys

import config
import logging_config
import web_app.db


def test_server_import_has_no_side_effects(monkeypatch):
    called = False

    def fake_setup_logging(*args, **kwargs):
        nonlocal called
        called = True

    def fake_load_config():
        raise AssertionError("load_config should not be called during import")

    monkeypatch.setattr(logging_config, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(config, "load_config", fake_load_config)
    monkeypatch.setattr(web_app.db, "init_db", lambda force_reset=False: None)

    sys.modules.pop("web_app.server", None)
    importlib.import_module("web_app.server")

    assert not called
