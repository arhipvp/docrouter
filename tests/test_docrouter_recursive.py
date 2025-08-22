import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from docrouter import process_directory
import metadata_generation


def test_process_directory_preserves_subdirs(tmp_path, monkeypatch):
    input_dir = tmp_path / "input" / "sub1" / "sub2"
    input_dir.mkdir(parents=True)
    file_path = input_dir / "data.txt"
    file_path.write_text("hello", encoding="utf-8")

    def fake_generate(text):
        return {"date": "2024-01-01"}

    monkeypatch.setattr(metadata_generation, "generate_metadata", fake_generate)

    dest_root = tmp_path / "Archive"
    process_directory(tmp_path / "input", dest_root)

    expected = dest_root / "sub1" / "sub2" / "2024-01-01__data.txt"
    assert expected.exists()
    assert not file_path.exists()
