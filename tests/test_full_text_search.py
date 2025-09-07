import importlib
import sys
import types
import asyncio

dummy_server = types.ModuleType("server")
dummy_server.app = None
sys.modules.setdefault("web_app.server", dummy_server)
db = importlib.import_module("web_app.db")
from models import Metadata


def test_full_text_search(tmp_path):
    original_path = db._DB_PATH
    original_conn = db._conn
    try:
        db._DB_PATH = tmp_path / "test.sqlite"
        db._conn = None
        asyncio.run(db.run_db(db.init_db))

        db.add_file("1", "a.pdf", Metadata(extracted_text="Иван Петров паспорт 1234"), "a.pdf")
        db.add_file("2", "b.pdf", Metadata(extracted_text="Анна Сидорова паспорт 5678"), "b.pdf")

        res1 = db.search_files("Иван")
        assert [r.id for r in res1] == ["1"]

        res2 = db.search_files("5678")
        assert [r.id for r in res2] == ["2"]
    finally:
        if db._conn is not None:
            db._conn.close()
        db._conn = original_conn
        db._DB_PATH = original_path

