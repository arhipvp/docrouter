import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

sys.modules.setdefault("cv2", types.SimpleNamespace())
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from file_sorter import get_folder_tree  # noqa: E402
from web_app import server  # noqa: E402


def test_get_folder_tree_returns_name_children(tmp_path):
    (tmp_path / "A" / "B").mkdir(parents=True)
    tree, _ = get_folder_tree(tmp_path)
    assert tree == [{"name": "A", "children": [{"name": "B", "children": []}]}]


def test_folder_tree_endpoint(tmp_path):
    (tmp_path / "X" / "Y").mkdir(parents=True)
    server.config.output_dir = str(tmp_path)
    client = TestClient(server.app)
    resp = client.get("/folder-tree")
    assert resp.status_code == 200
    assert resp.json() == [{"name": "X", "children": [{"name": "Y", "children": []}]}]
