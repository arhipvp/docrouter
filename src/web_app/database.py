from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Union

from config import load_config

config = load_config()
# Используем нижний регистр, соответствующий определению в Config
DB_PATH: Union[str, Path] = config.db_url or "metadata.db"
if DB_PATH != ":memory:":
    DB_PATH = Path(DB_PATH)


def init_db() -> None:
    """Initialize the SQLite database and create tables if needed."""
    if isinstance(DB_PATH, Path):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                metadata TEXT NOT NULL,
                path TEXT,
                status TEXT
            )
            """
        )


def add_file(file_id: str, metadata: Dict[str, Any], path: str, status: str) -> None:
    """Insert a file record into the database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO files (id, metadata, path, status) VALUES (?, ?, ?, ?)",
            (file_id, json.dumps(metadata), path, status),
        )


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a file record by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, metadata, path, status FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
        if row is None:
            return None
        data = json.loads(row["metadata"])
        return {
            "id": row["id"],
            "metadata": data,
            "path": row["path"],
            "status": row["status"],
        }


def update_file(file_id: str, metadata: Dict[str, Any], path: str, status: str) -> None:
    """Update an existing file record."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE files SET metadata = ?, path = ?, status = ? WHERE id = ?",
            (json.dumps(metadata), path, status, file_id),
        )


def delete_file(file_id: str) -> None:
    """Delete a file record from the database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
