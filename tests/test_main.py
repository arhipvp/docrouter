import sys
import types
from pathlib import Path

import pytest

# Stub external dependencies to avoid heavy installations
yaml_stub = types.SimpleNamespace(safe_load=lambda *a, **k: {})
sys.modules.setdefault("yaml", yaml_stub)

requests_stub = types.SimpleNamespace()
sys.modules.setdefault("requests", requests_stub)

PIL_module = types.ModuleType("PIL")
image_module = types.ModuleType("Image")
image_module.open = lambda path: path
PIL_module.Image = image_module
sys.modules.setdefault("PIL", PIL_module)
sys.modules.setdefault("PIL.Image", image_module)

pytesseract_stub = types.SimpleNamespace(image_to_string=lambda img: "")
sys.modules.setdefault("pytesseract", pytesseract_stub)

# Ensure repository root is on path for importing main
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


def test_main_success(monkeypatch, tmp_path, caplog):
    monkeypatch.delenv("DRY_RUN", raising=False)
    docs = [tmp_path / "a.txt", tmp_path / "b.txt"]

    monkeypatch.setattr(main.scanner, "list_documents", lambda p: docs)

    def fake_extract(path):
        return f"text-{path.name}"

    monkeypatch.setattr(main.extractor, "extract_text", fake_extract)
    monkeypatch.setattr(main.llm_client, "analyze_text", lambda text: {"summary": text})
    saved = []
    monkeypatch.setattr(main.saver, "store_document", lambda path, meta: saved.append((path, meta)))

    caplog.set_level("INFO")
    main.main([str(tmp_path)])

    assert saved == [
        (docs[0], {"summary": "text-a.txt"}),
        (docs[1], {"summary": "text-b.txt"}),
    ]
    assert "Processed 2 files" in caplog.text


def test_main_dry_run_and_error(monkeypatch, tmp_path):
    monkeypatch.delenv("DRY_RUN", raising=False)
    docs = [tmp_path / "a.txt", tmp_path / "b.txt"]
    monkeypatch.setattr(main.scanner, "list_documents", lambda p: docs)

    def fake_extract(path):
        if path.name == "b.txt":
            raise RuntimeError("boom")
        return "ok"

    monkeypatch.setattr(main.extractor, "extract_text", fake_extract)
    monkeypatch.setattr(main.llm_client, "analyze_text", lambda text: {"summary": text})
    saved = []
    monkeypatch.setattr(main.saver, "store_document", lambda path, meta: saved.append((path, meta)))
    handled = []
    monkeypatch.setattr(
        main.error_handler, "handle_error", lambda path, err: handled.append((path, str(err)))
    )

    main.main([str(tmp_path), "--dry-run"])

    assert saved == []  # dry-run skips saving
    assert handled == [(docs[1], "boom")]
