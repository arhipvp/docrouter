from __future__ import annotations

"""Хранилище метаданных на SQLite."""

from pathlib import Path
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from models import FileRecord, Metadata

_DB_PATH = Path(__file__).with_suffix(".sqlite")
_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("DB is not initialized, call init_db() first")
    return _conn


def init_db(force_reset: bool | None = None) -> None:
    """Создать таблицы.

    Параметр ``force_reset`` или переменная окружения ``DOCROUTER_RESET_DB``
    (значение ``1``) приводит к удалению существующей схемы.
    """
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass

    if force_reset is None:
        force_reset = os.getenv("DOCROUTER_RESET_DB") == "1"

    _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    with _conn:
        if force_reset:
            _conn.execute("DROP TABLE IF EXISTS files")
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                metadata TEXT NOT NULL,
                tags_ru TEXT,
                tags_en TEXT,
                person TEXT,
                date_of_birth TEXT,
                expiration_date TEXT,
                passport_number TEXT,
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'review',
                prompt TEXT,
                raw_response TEXT,
                missing TEXT,
                translated_text TEXT,
                translation_lang TEXT,
                chat_history TEXT,
                review_comment TEXT,
                sources TEXT,
                suggested_path TEXT,
                created_path TEXT,
                confirmed INTEGER
            )
            """
        )
        _conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_files_id ON files(id)"
        )


def close_db() -> None:
    """Закрыть соединение с БД и сбросить ссылку."""
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        finally:
            _conn = None


def _serialize_record(record: FileRecord) -> Dict[str, Any]:
    return {
        "id": record.id,
        "filename": record.filename,
        "metadata": json.dumps(record.metadata.model_dump(), ensure_ascii=False),
        "tags_ru": json.dumps(record.tags_ru, ensure_ascii=False),
        "tags_en": json.dumps(record.tags_en, ensure_ascii=False),
        "person": record.person,
        "date_of_birth": record.date_of_birth,
        "expiration_date": record.expiration_date,
        "passport_number": record.passport_number,
        "path": record.path,
        "status": record.status,
        "prompt": json.dumps(record.prompt, ensure_ascii=False) if record.prompt is not None else None,
        "raw_response": json.dumps(record.raw_response, ensure_ascii=False) if record.raw_response is not None else None,
        "missing": json.dumps(record.missing, ensure_ascii=False),
        "translated_text": record.translated_text,
        "translation_lang": record.translation_lang,
        "chat_history": json.dumps(record.chat_history, ensure_ascii=False),
        "review_comment": record.review_comment,
        "sources": json.dumps(record.sources, ensure_ascii=False) if record.sources is not None else None,
        "suggested_path": record.suggested_path,
        "created_path": record.created_path,
        "confirmed": 1 if record.confirmed else 0,
    }


def _row_to_record(row: sqlite3.Row) -> FileRecord:
    metadata_dict = json.loads(row["metadata"]) if row["metadata"] else {}
    return FileRecord(
        id=row["id"],
        filename=row["filename"],
        metadata=Metadata(**metadata_dict),
        tags_ru=json.loads(row["tags_ru"]) if row["tags_ru"] else [],
        tags_en=json.loads(row["tags_en"]) if row["tags_en"] else [],
        person=row["person"],
        date_of_birth=row["date_of_birth"],
        expiration_date=row["expiration_date"],
        passport_number=row["passport_number"],
        path=row["path"],
        status=row["status"],
        prompt=json.loads(row["prompt"]) if row["prompt"] else None,
        raw_response=json.loads(row["raw_response"]) if row["raw_response"] else None,
        missing=json.loads(row["missing"]) if row["missing"] else [],
        translated_text=row["translated_text"],
        translation_lang=row["translation_lang"],
        chat_history=json.loads(row["chat_history"]) if row["chat_history"] else [],
        review_comment=row["review_comment"],
        sources=json.loads(row["sources"]) if row["sources"] else None,
        suggested_path=row["suggested_path"],
        created_path=row["created_path"],
        confirmed=bool(row["confirmed"]),
    )


def _upsert(record: FileRecord) -> None:
    conn = _get_conn()
    data = _serialize_record(record)
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with conn:
        conn.execute(
            f"REPLACE INTO files ({columns}) VALUES ({placeholders})",
            tuple(data.values()),
        )


def add_file(
    file_id: str,
    filename: str,
    metadata: Metadata,
    path: str,
    status: str = "review",
    prompt: Any | None = None,
    raw_response: Any | None = None,
    missing: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    translated_text: str | None = None,
    translation_lang: str | None = None,
    suggested_path: str | None = None,
    confirmed: bool = False,
    created_path: str | None = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    review_comment: str | None = None,
) -> None:
    record = FileRecord(
        id=file_id,
        filename=filename,
        metadata=metadata,
        tags_ru=metadata.tags_ru,
        tags_en=metadata.tags_en,
        person=metadata.person,
        date_of_birth=metadata.date_of_birth,
        expiration_date=metadata.expiration_date,
        passport_number=metadata.passport_number,
        path=path,
        status=status,
        prompt=prompt,
        raw_response=raw_response,
        missing=missing or [],
        translated_text=translated_text,
        translation_lang=translation_lang,
        chat_history=chat_history or [],
        review_comment=review_comment,
        sources=sources,
        suggested_path=suggested_path,
        created_path=created_path,
        confirmed=confirmed,
    )
    _upsert(record)


def get_file(file_id: str) -> Optional[FileRecord]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def get_details(file_id: str) -> Optional[FileRecord]:
    return get_file(file_id)


def update_file(
    file_id: str,
    metadata: Optional[Metadata] = None,
    path: str | None = None,
    status: str | None = None,
    prompt: Any | None = None,
    raw_response: Any | None = None,
    missing: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    translated_text: str | None = None,
    translation_lang: str | None = None,
    suggested_path: str | None = None,
    confirmed: bool | None = None,
    created_path: str | None = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    review_comment: str | None = None,
) -> None:
    record = get_file(file_id)
    if record is None:
        return
    if metadata:
        record.metadata = record.metadata.model_copy(update=metadata.model_dump(exclude_unset=True))
        record.tags_ru = record.metadata.tags_ru
        record.tags_en = record.metadata.tags_en
        record.person = record.metadata.person
        record.date_of_birth = record.metadata.date_of_birth
        record.expiration_date = record.metadata.expiration_date
        record.passport_number = record.metadata.passport_number
    if path is not None:
        record.path = path
    if status is not None:
        record.status = status
    if prompt is not None:
        record.prompt = prompt
    if raw_response is not None:
        record.raw_response = raw_response
    if missing is not None:
        record.missing = missing
    if sources is not None:
        record.sources = sources
    if translated_text is not None:
        record.translated_text = translated_text
    if translation_lang is not None:
        record.translation_lang = translation_lang
    if suggested_path is not None:
        record.suggested_path = suggested_path
    if confirmed is not None:
        record.confirmed = confirmed
    if created_path is not None:
        record.created_path = created_path
    if chat_history is not None:
        record.chat_history = chat_history
    if review_comment is not None:
        record.review_comment = review_comment
    _upsert(record)


def delete_file(file_id: str) -> None:
    conn = _get_conn()
    with conn:
        conn.execute("DELETE FROM files WHERE id=?", (file_id,))


def list_files() -> List[FileRecord]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM files").fetchall()
    return [_row_to_record(r) for r in rows]


def search_files(query: str) -> List[FileRecord]:
    conn = _get_conn()
    pattern = f"%{query}%"
    rows = conn.execute(
        """
        SELECT * FROM files
        WHERE metadata LIKE ?
           OR person LIKE ?
           OR passport_number LIKE ?
        """,
        (pattern, pattern, pattern),
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def add_chat_message(
    file_id: str,
    role: str,
    message: str,
    tokens: int | None = None,
    cost: float | None = None,
) -> List[Dict[str, Any]]:
    record = get_file(file_id)
    if record is None:
        return []
    history = record.chat_history
    entry: Dict[str, Any] = {"role": role, "message": message}
    if tokens is not None:
        entry["tokens"] = tokens
    if cost is not None:
        entry["cost"] = cost
    history.append(entry)
    record.chat_history = history
    _upsert(record)
    return history


def get_chat_history(file_id: str) -> List[Dict[str, Any]]:
    record = get_file(file_id)
    if record is None:
        return []
    return record.chat_history
