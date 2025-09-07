import sys
from pathlib import Path

from fastapi.testclient import TestClient
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from file_sorter import get_folder_tree  # noqa: E402
from web_app import server  # noqa: E402


def test_get_folder_tree_returns_name_children(tmp_path):
    (tmp_path / "A" / "B").mkdir(parents=True)
    tree, _ = get_folder_tree(tmp_path)
    assert tree == [
        {
            "name": "A",
            "path": "A",
            "children": [
                {"name": "B", "path": "A/B", "children": [], "files": []}
            ],
            "files": [],
        }
    ]


def test_folder_tree_endpoint(tmp_path):
    (tmp_path / "X" / "Y").mkdir(parents=True)
    server.config.output_dir = str(tmp_path)
    server.database.init_db()
    client = TestClient(server.app)
    resp = client.get("/folder-tree")
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "name": "X",
            "path": "X",
            "children": [
                {"name": "Y", "path": "X/Y", "children": [], "files": []}
            ],
            "files": [],
        }
    ]
