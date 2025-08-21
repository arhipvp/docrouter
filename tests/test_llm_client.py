import pytest
import requests
from src.llm_client import analyze_text


def _prepare_config(monkeypatch, tmp_path, content="model: test-model\n"):
    cfg = tmp_path / "config.yml"
    cfg.write_text(content, encoding="utf-8")
    monkeypatch.setenv("DOCROUTER_CONFIG", str(cfg))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")


def test_analyze_text_success(monkeypatch, tmp_path):
    _prepare_config(monkeypatch, tmp_path)

    def fake_post(url, headers=None, json=None, timeout=None):
        assert json["model"] == "test-model"
        assert json["messages"][0]["content"] == "hello"

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"result": "ok"}

        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)

    assert analyze_text("hello") == {"result": "ok"}


def test_analyze_text_network_error(monkeypatch, tmp_path):
    _prepare_config(monkeypatch, tmp_path)

    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        analyze_text("data")


def test_analyze_text_invalid_json(monkeypatch, tmp_path):
    _prepare_config(monkeypatch, tmp_path)

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("not json")

    def fake_post(*args, **kwargs):
        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        analyze_text("data")
