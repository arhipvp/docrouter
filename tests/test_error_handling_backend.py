import json

from error_handling import handle_error


def test_handle_error_moves_file_and_creates_json(tmp_path):
    bad_file = tmp_path / "bad.xyz"
    bad_file.write_text("data", encoding="utf-8")

    handle_error(bad_file, ValueError("boom"), unsorted_dir=tmp_path / "Unsorted", errors_dir=tmp_path / "errors")

    moved = tmp_path / "Unsorted" / "bad.xyz"
    assert moved.exists()

    error_json = tmp_path / "errors" / "bad.xyz.json"
    assert error_json.exists()
    data = json.loads(error_json.read_text(encoding="utf-8"))
    assert "boom" in data["error"]
