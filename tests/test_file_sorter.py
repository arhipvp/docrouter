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


def test_place_file_path_and_name(tmp_path):
    src = tmp_path / "input.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    # dry_run: ничего не создаётся, но пути и missing рассчитываются
    dest, missing = place_file(src, sample_metadata(), dest_root, dry_run=True)

    expected = dest_root / "Финансы" / "Банки" / "Sparkasse" / "2023-10-12__Kreditvertrag.pdf"
    assert dest == expected
    assert missing == [
        "Финансы",
        "Финансы/Банки",
        "Финансы/Банки/Sparkasse",
    ]


def test_place_file_moves_and_creates_json(tmp_path):
    src = tmp_path / "document.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    # По умолчанию create_missing=True — каталоги будут созданы, файл перемещён
    dest, missing = place_file(src, sample_metadata(), dest_root, dry_run=False)

    json_path = dest.with_suffix(dest.suffix + ".json")
    assert dest.exists()
    assert json_path.exists()
    assert missing == []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["issuer"] == "Sparkasse"


def test_place_file_renames_on_name_conflict(tmp_path):
    src1 = tmp_path / "file1.pdf"
    src1.write_text("a")
    src2 = tmp_path / "file2.pdf"
    src2.write_text("b")

    dest_root = tmp_path / "Archive"

    dest1, _ = place_file(src1, sample_metadata(), dest_root, dry_run=False)
    dest2, _ = place_file(src2, sample_metadata(), dest_root, dry_run=False)

    assert dest1.name == "2023-10-12__Kreditvertrag.pdf"
    assert dest2.name == "2023-10-12__Kreditvertrag_1.pdf"
    assert dest2.exists()
    assert dest2.with_suffix(dest2.suffix + ".json").exists()


def test_place_file_sanitizes_invalid_chars(tmp_path):
    src = tmp_path / "report.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["suggested_name"] = "inva:lid/na*me?"

    dest, _ = place_file(src, metadata, dest_root, dry_run=True)

    assert dest.name == "2023-10-12__inva_lid_na_me_.pdf"


def test_place_file_returns_missing_dirs_and_does_not_move_when_create_missing_false(tmp_path):
    src = tmp_path / "document.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    dest, missing = place_file(
        src, sample_metadata(), dest_root, dry_run=False, create_missing=False
    )

    assert missing == [
        "Финансы",
        "Финансы/Банки",
        "Финансы/Банки/Sparkasse",
    ]
    # файл не должен быть перемещён
    assert not dest.exists()
    assert src.exists()


def test_place_file_generates_transliteration(tmp_path):
    pytest.importorskip("unidecode")
    src = tmp_path / "doc.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["suggested_name"] = "тест"

    place_file(src, metadata, dest_root, dry_run=True)

    assert metadata["suggested_name_translit"] == "test"
