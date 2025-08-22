from __future__ import annotations

"""Простейшее хранилище метаданных в памяти."""

from typing import Any, Dict, Optional, List

# Внутренний словарь для хранения записей
_storage: Dict[str, Dict[str, Any]] = {}


def init_db() -> None:
    """Инициализировать/очистить хранилище."""
    _storage.clear()


def add_file(
    file_id: str,
    filename: str,
    metadata: Dict[str, Any],
    path: str,
    status: str,
    prompt: Any | None = None,
    raw_response: Any | None = None,
    missing: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    translated_text: str | None = None,
    translation_lang: str | None = None,
    embedding: list[float] | None = None,
) -> None:
    """Сохранить информацию о файле."""
    _storage[file_id] = {
        "id": file_id,
        "filename": filename,
        "metadata": metadata,
        "tags_ru": metadata.get("tags_ru", []),
        "tags_en": metadata.get("tags_en", []),
        "person": metadata.get("person"),
        "date_of_birth": metadata.get("date_of_birth"),
        "expiration_date": metadata.get("expiration_date"),
        "passport_number": metadata.get("passport_number"),
        "path": path,
        "status": status,
        "prompt": prompt,
        "raw_response": raw_response,
        "missing": missing or [],
        "translated_text": translated_text,
        "translation_lang": translation_lang,
        "chat_history": [],
    }
    if sources is not None:
        _storage[file_id]["sources"] = sources
    if embedding is not None:
        _storage[file_id]["embedding"] = embedding


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Получить информацию о файле по ID."""
    return _storage.get(file_id)


def get_details(file_id: str) -> Optional[Dict[str, Any]]:
    """Вернуть полную запись без фильтрации полей."""
    return _storage.get(file_id)


def update_file(
    file_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    path: str | None = None,
    status: str | None = None,
    prompt: Any | None = None,
    raw_response: Any | None = None,
    missing: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    translated_text: str | None = None,
    translation_lang: str | None = None,
    embedding: list[float] | None = None,
) -> None:
    """Обновить данные существующей записи."""
    record = _storage.get(file_id)
    if record is None:
        return

    if metadata:
        record.setdefault("metadata", {}).update(metadata)
        if "tags_ru" in metadata:
            record["tags_ru"] = metadata["tags_ru"]
        if "tags_en" in metadata:
            record["tags_en"] = metadata["tags_en"]
        if "person" in metadata:
            record["person"] = metadata["person"]
        if "date_of_birth" in metadata:
            record["date_of_birth"] = metadata["date_of_birth"]
        if "expiration_date" in metadata:
            record["expiration_date"] = metadata["expiration_date"]
        if "passport_number" in metadata:
            record["passport_number"] = metadata["passport_number"]

    if path is not None:
        record["path"] = path
    if status is not None:
        record["status"] = status
    if prompt is not None:
        record["prompt"] = prompt
    if raw_response is not None:
        record["raw_response"] = raw_response
    if missing is not None:
        record["missing"] = missing
    if sources is not None:
        record["sources"] = sources
    if translated_text is not None:
        record["translated_text"] = translated_text
    if translation_lang is not None:
        record["translation_lang"] = translation_lang
    if embedding is not None:
        record["embedding"] = embedding


def delete_file(file_id: str) -> None:
    """Удалить запись о файле."""
    _storage.pop(file_id, None)


def list_files() -> list[Dict[str, Any]]:
    """Получить список всех файлов."""
    return list(_storage.values())


def add_chat_message(file_id: str, role: str, message: str) -> List[Dict[str, str]]:
    """Добавить запись в историю чата."""
    record = _storage.get(file_id)
    if record is None:
        return []
    history: List[Dict[str, str]] = record.setdefault("chat_history", [])
    history.append({"role": role, "message": message})
    return history


def get_chat_history(file_id: str) -> List[Dict[str, str]]:
    """Получить историю чата по файлу."""
    record = _storage.get(file_id)
    if record is None:
        return []
    return record.setdefault("chat_history", [])
