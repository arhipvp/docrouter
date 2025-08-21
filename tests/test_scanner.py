import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scanner import list_documents


def test_list_documents_filters_hidden_and_temp(tmp_path: Path) -> None:
    (tmp_path / "visible.txt").touch()
    (tmp_path / ".hidden.txt").touch()
    (tmp_path / "tempfile~").touch()
    (tmp_path / "~temp.txt").touch()
    (tmp_path / "#temp#").touch()

    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "inner.txt").touch()
    (sub / ".hidden_inner.txt").touch()
    (sub / "inner_temp~").touch()

    hidden_dir = tmp_path / ".hidden_dir"
    hidden_dir.mkdir()
    (hidden_dir / "inside_hidden.txt").touch()

    temp_dir = sub / "~tempdir"
    temp_dir.mkdir()
    (temp_dir / "inside_temp.txt").touch()

    expected = sorted([tmp_path / "visible.txt", sub / "inner.txt"])
    assert list_documents(tmp_path) == expected
