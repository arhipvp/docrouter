import sys
import json
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from file_sorter import place_file
from config import config


def sample_metadata():
    return {
        "category": "Финансы",
        "subcategory": "Банки",
        "issuer": "Sparkasse",
        "date": "2023-10-12",
        "suggested_name": "Kreditvertrag",
        "suggested_filename": "Kreditvertrag.pdf",
    }


def test_place_file_path_and_name(tmp_path):
    src = tmp_path / "input.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    # dry_run: ничего не создаётся, но пути и missing рассчитываются
    dest, missing, _ = place_file(src, sample_metadata(), dest_root, dry_run=True)

    expected = (
        dest_root
        / config.general_folder_name
        / "Финансы"
        / "Банки"
        / "Sparkasse"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert dest == expected
    assert missing == [
        f"{config.general_folder_name}",
        f"{config.general_folder_name}/Финансы",
        f"{config.general_folder_name}/Финансы/Банки",
        f"{config.general_folder_name}/Финансы/Банки/Sparkasse",
    ]


def test_place_file_uses_person_folder(tmp_path):
    src = tmp_path / "input.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["person"] = "Alice"
    dest, missing, _ = place_file(src, metadata, dest_root, dry_run=True)

    expected = (
        dest_root
        / "Alice"
        / "Финансы"
        / "Банки"
        / "Sparkasse"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert dest == expected
    assert missing == [
        "Alice",
        "Alice/Финансы",
        "Alice/Финансы/Банки",
        "Alice/Финансы/Банки/Sparkasse",
    ]


def test_place_file_uses_person_from_metadata(tmp_path):
    src = tmp_path / "input.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["person"] = "Alice"
    dest, missing, _ = place_file(src, metadata, dest_root, dry_run=True)

    expected = (
        dest_root / "Alice" / "Финансы" / "Банки" / "Sparkasse" / "2023-10-12__Kreditvertrag.pdf"
    )
    assert dest == expected
    assert missing == [
        "Alice",
        "Alice/Финансы",
        "Alice/Финансы/Банки",
        "Alice/Финансы/Банки/Sparkasse",
    ]


def test_place_file_ignores_person_in_category(tmp_path):
    src = tmp_path / "input.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["person"] = "Иванов Иван"
    metadata["category"] = "Иванов Иван"
    metadata["subcategory"] = "Иванов Иван"
    dest, missing, _ = place_file(src, metadata, dest_root, dry_run=True)

    expected = dest_root / "Иванов Иван" / "Sparkasse" / "2023-10-12__Kreditvertrag.pdf"
    assert dest == expected
    assert missing == [
        "Иванов Иван",
        "Иванов Иван/Sparkasse",
    ]


def test_place_file_uses_general_when_person_empty(tmp_path):
    src = tmp_path / "input.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["person"] = "  "  # пустая строка после trim
    dest, missing, _ = place_file(src, metadata, dest_root, dry_run=True)

    expected = (
        dest_root
        / config.general_folder_name
        / "Финансы"
        / "Банки"
        / "Sparkasse"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert dest == expected
    assert missing == [
        f"{config.general_folder_name}",
        f"{config.general_folder_name}/Финансы",
        f"{config.general_folder_name}/Финансы/Банки",
        f"{config.general_folder_name}/Финансы/Банки/Sparkasse",
    ]


def test_place_file_prefers_suggested_name(tmp_path):
    src = tmp_path / "file.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["suggested_filename"] = "other.pdf"

    dest, _, _ = place_file(src, metadata, dest_root, dry_run=True)
    assert dest.name == "2023-10-12__Kreditvertrag.pdf"


def test_place_file_moves_and_creates_json(tmp_path):
    src = tmp_path / "document.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    # Каталоги будут созданы, файл перемещён
    dest, missing, confirmed = place_file(
        src,
        sample_metadata(),
        dest_root,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _: True,
    )

    json_path = dest.with_suffix(dest.suffix + ".json")
    expected = (
        dest_root
        / config.general_folder_name
        / "Финансы"
        / "Банки"
        / "Sparkasse"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert dest == expected
    assert dest.exists()
    assert json_path.exists()
    assert missing == []
    assert confirmed is True

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["issuer"] == "Sparkasse"


def test_place_file_renames_on_name_conflict(tmp_path):
    src1 = tmp_path / "file1.pdf"
    src1.write_text("a")
    src2 = tmp_path / "file2.pdf"
    src2.write_text("b")

    dest_root = tmp_path / "Archive"

    dest1, _, _ = place_file(
        src1,
        sample_metadata(),
        dest_root,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _: True,
    )
    dest2, _, _ = place_file(
        src2,
        sample_metadata(),
        dest_root,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _: True,
    )

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

    dest, _, _ = place_file(src, metadata, dest_root, dry_run=True)

    assert dest.name == "2023-10-12__inva_lid_na_me_.pdf"


def test_place_file_sanitizes_dirnames(tmp_path):
    src = tmp_path / "report.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["person"] = "../evil"
    metadata["category"] = "../cat"
    metadata["subcategory"] = "../sub"
    metadata["issuer"] = "../iss"

    dest, _, _ = place_file(src, metadata, dest_root, dry_run=True)
    assert dest == (
        dest_root
        / "evil"
        / "cat"
        / "sub"
        / "iss"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert metadata["person"] == "evil"
    assert metadata["category"] == "cat"
    assert metadata["subcategory"] == "sub"
    assert metadata["issuer"] == "iss"


def test_place_file_removes_date_from_suggested_name(tmp_path):
    src = tmp_path / "report.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["suggested_name"] = "2023-10-12 Kreditvertrag"

    dest, _, _ = place_file(src, metadata, dest_root, dry_run=True)

    assert dest.name == "2023-10-12__Kreditvertrag.pdf"
    assert dest.name.count("2023-10-12") == 1


def test_place_file_returns_missing_dirs_and_does_not_move_when_needs_new_folder_false(tmp_path):
    src = tmp_path / "document.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    dest, missing, confirmed = place_file(
        src,
        sample_metadata(),
        dest_root,
        dry_run=False,
        needs_new_folder=False,
    )

    expected = (
        dest_root
        / config.general_folder_name
        / "Финансы"
        / "Банки"
        / "Sparkasse"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert dest == expected
    assert missing == [
        f"{config.general_folder_name}",
        f"{config.general_folder_name}/Финансы",
        f"{config.general_folder_name}/Финансы/Банки",
        f"{config.general_folder_name}/Финансы/Банки/Sparkasse",
    ]
    # файл не должен быть перемещён
    assert not dest.exists()
    assert src.exists()
    assert confirmed is False


def test_place_file_missing_then_confirm_creation(tmp_path):
    src = tmp_path / "doc.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"

    # Первый вызов: каталоги отсутствуют, подтверждения нет
    dest, missing, confirmed = place_file(
        src,
        sample_metadata(),
        dest_root,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _: False,
    )

    expected = (
        dest_root
        / config.general_folder_name
        / "Финансы"
        / "Банки"
        / "Sparkasse"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert dest == expected
    assert missing == [
        f"{config.general_folder_name}",
        f"{config.general_folder_name}/Финансы",
        f"{config.general_folder_name}/Финансы/Банки",
        f"{config.general_folder_name}/Финансы/Банки/Sparkasse",
    ]
    assert not dest.exists()
    assert src.exists()
    assert confirmed is False

    # Повторный вызов с подтверждением создаёт каталоги и переносит файл
    dest2, missing2, confirmed2 = place_file(
        src,
        sample_metadata(),
        dest_root,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _: True,
    )

    assert dest2 == expected
    assert missing2 == []
    assert confirmed2 is True
    assert dest2.exists()
    assert not src.exists()


def test_place_file_generates_transliteration(tmp_path):
    pytest.importorskip("unidecode")
    src = tmp_path / "doc.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["suggested_name"] = "тест"

    place_file(src, metadata, dest_root, dry_run=True)

    assert metadata["suggested_name_translit"] == "test"


def test_place_file_creates_dirs_on_confirmation(tmp_path):
    src = tmp_path / "doc.pdf"
    src.write_text("content")

    dest_root = tmp_path / "Archive"
    dest, missing, confirmed = place_file(
        src,
        sample_metadata(),
        dest_root,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _: True,
    )

    expected = (
        dest_root
        / config.general_folder_name
        / "Финансы"
        / "Банки"
        / "Sparkasse"
        / "2023-10-12__Kreditvertrag.pdf"
    )
    assert confirmed is True
    assert missing == []
    assert dest == expected
    assert dest.exists()
    assert dest.parent.exists()


def test_place_file_handles_missing_and_valid_date(tmp_path):
    src = tmp_path / "doc.pdf"
    src.write_text("data")

    dest_root = tmp_path / "Archive"
    metadata = sample_metadata()
    metadata["date"] = None
    dest, _, _ = place_file(src, metadata, dest_root, dry_run=True)
    assert dest.name.startswith("unknown-date__")

    metadata["date"] = "2024-07-05"
    dest2, _, _ = place_file(src, metadata, dest_root, dry_run=True)
    assert dest2.name.startswith("2024-07-05__")
