import sqlite3
import web_app.db as db
import pytest
import asyncio


def test_close_and_reopen_db(tmp_path):
    original_path = db._DB_PATH
    original_conn = db._conn
    try:
        db._DB_PATH = tmp_path / "test.sqlite"
        db._conn = None
        asyncio.run(db.run_db(db.init_db))
        conn1 = db._conn
        assert conn1 is not None

        db.close_db()
        assert db._conn is None
        with pytest.raises(sqlite3.ProgrammingError):
            conn1.execute("SELECT 1")

        asyncio.run(db.run_db(db.init_db))
        conn2 = db._conn
        assert conn2 is not None
        assert conn2 is not conn1
    finally:
        db.close_db()
        db._DB_PATH = original_path
        db._conn = original_conn
