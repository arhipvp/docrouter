import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from saver import store_document


def test_store_document_uses_person(tmp_path, monkeypatch):
    source = tmp_path / "input.txt"
    source.write_text("data", encoding="utf-8")
    metadata = {
        "категория": "Платежи",
        "подкатегория": "Коммунальные",
        "человек": "Иван",
    }

    monkeypatch.chdir(tmp_path)
    dest = store_document(source, metadata)

    expected = tmp_path / "Архив" / "Платежи" / "Коммунальные" / "Иван" / "input.txt"
    assert dest == expected and dest.exists()
    assert dest.read_text(encoding="utf-8") == "data"

    meta_path = dest.with_suffix(dest.suffix + ".json")
    saved_metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved_metadata == metadata


def test_store_document_uses_organization(tmp_path, monkeypatch):
    source = tmp_path / "doc.pdf"
    source.write_text("content", encoding="utf-8")
    metadata = {
        "категория": "Отчёты",
        "подкатегория": "Годовой",
        "организация": "ООО Ромашка",
    }

    monkeypatch.chdir(tmp_path)
    dest = store_document(source, metadata)

    expected = tmp_path / "Архив" / "Отчёты" / "Годовой" / "ООО Ромашка" / "doc.pdf"
    assert dest == expected and dest.exists()

    meta_path = dest.with_suffix(dest.suffix + ".json")
    saved_metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved_metadata == metadata
