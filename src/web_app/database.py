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
) -> None:
    """Сохранить информацию о файле."""
    _storage[file_id] = {
        "id": file_id,
        "filename": filename,
        "metadata": metadata,
        "path": path,
        "status": status,
        "prompt": prompt,
        "raw_response": raw_response,
        "missing": missing or [],
    }


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Получить информацию о файле по ID."""
    return _storage.get(file_id)


def get_details(file_id: str) -> Optional[Dict[str, Any]]:
    """Вернуть полную запись без фильтрации полей."""
    return _storage.get(file_id)


def update_file(
    file_id: str,
    metadata: Dict[str, Any],
    path: str,
    status: str,
    prompt: Any | None = None,
    raw_response: Any | None = None,
    missing: Optional[List[str]] = None,
) -> None:
    """Обновить данные существующей записи."""
    if file_id in _storage:
        _storage[file_id].update(
            {
                "metadata": metadata,
                "path": path,
                "status": status,
                "prompt": prompt,
                "raw_response": raw_response,
                "missing": missing or [],
            }
        )


def delete_file(file_id: str) -> None:
    """Удалить запись о файле."""
    _storage.pop(file_id, None)


def list_files() -> list[Dict[str, Any]]:
    """Получить список всех файлов."""
    return list(_storage.values())

