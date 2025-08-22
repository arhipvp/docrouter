import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from file_sorter import place_file


def sample_metadata():
    return {
        "category": "Финансы",
        "subcategory": "Банки",
        "issuer": "Sparkasse",
        "date": "2023-10-12",
        "suggested_name": "Kreditvertrag",
    }


def test_place_file_path_and_name(tmp_path, capsys):
    src = tmp_path / "input.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    dest = place_file(src, sample_metadata(), dest_root, dry_run=True)

    expected = dest_root / "Финансы" / "Банки" / "Sparkasse" / "2023-10-12__Kreditvertrag.pdf"
    assert dest == expected


def test_place_file_moves_and_creates_json(tmp_path):
    src = tmp_path / "document.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    dest = place_file(src, sample_metadata(), dest_root, dry_run=False)

    json_path = dest.with_suffix(dest.suffix + ".json")
    assert dest.exists()
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["issuer"] == "Sparkasse"


def test_place_file_sanitizes_invalid_chars(tmp_path):
    src = tmp_path / "report.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["suggested_name"] = "inva:lid/na*me?"

    dest = place_file(src, metadata, dest_root, dry_run=True)

    assert dest.name == "2023-10-12__inva_lid_na_me_.pdf"
