import os
import sys

import pytest
import uvicorn
import httpx

# Add src to sys.path and configure server output dir before importing server
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["DB_URL"] = ":memory:"


from web_app import server  # noqa: E402

app = server.app


class LiveClient:
    def __init__(self, app, host: str = "127.0.0.1", port: int = 8002):
        self.app = app
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    def __enter__(self):
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="error")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        while not getattr(self.server, "started", False):
            time.sleep(0.01)
        self.session = httpx.Client()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.should_exit = True
        self.thread.join()
        self.session.close()

    def get(self, path, **kwargs):
        return self.session.get(self.base_url + path, **kwargs)


import threading
import time


def test_folder_tree_includes_files(tmp_path):
    # Create directory structure
    person = tmp_path / "John" / "Docs"
    person.mkdir(parents=True)
    (person / "file1.txt").write_text("content", encoding="utf-8")

    server.config.output_dir = str(tmp_path)
    server.database.init_db()

    with LiveClient(app) as client:
        resp = client.get("/folder-tree")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) and data
        john = data[0]
        assert john["name"] == "John"
        docs = john["children"][0]
        assert docs["name"] == "Docs"
        files = docs["files"]
        assert files and files[0]["name"] == "file1.txt"
        assert files[0]["path"].endswith("file1.txt")

