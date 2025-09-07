from file_sorter import place_file
from config import GENERAL_FOLDER_NAME
from web_app import db as database
from models import Metadata


def test_place_file_returns_missing_and_preserves_file(tmp_path):
    input_dir = tmp_path / "input" / "sub1" / "sub2"
    input_dir.mkdir(parents=True)
    file_path = input_dir / "data.txt"
    file_path.write_text("hello", encoding="utf-8")

    metadata = {"date": "2024-01-01", "category": "sub1", "subcategory": "sub2"}
    dest_root = tmp_path / "Archive"

    database.init_db()

    dest, missing, confirmed = place_file(
        file_path,
        metadata,
        dest_root,
        dry_run=False,
        needs_new_folder=True,
        confirm_callback=lambda _paths: False,
    )

    expected = dest_root / GENERAL_FOLDER_NAME / "sub1" / "sub2" / "2024-01-01__data.txt"
    assert dest == expected
    assert not dest.exists()
    assert file_path.exists()
    assert missing == [
        f"{GENERAL_FOLDER_NAME}",
        f"{GENERAL_FOLDER_NAME}/sub1",
        f"{GENERAL_FOLDER_NAME}/sub1/sub2",
    ]
    assert confirmed is False

    database.add_file(
        "1",
        file_path.name,
        Metadata(**metadata),
        str(file_path),
        "pending",
        suggested_path=str(dest),
        missing=missing,
    )
    records = database.list_files()
    assert len(records) == 1
    rec = records[0]
    assert rec.status == "pending"
    assert rec.suggested_path == str(expected)
