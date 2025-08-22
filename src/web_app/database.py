from __future__ import annotations

"""Простейшее хранилище метаданных в памяти."""

from typing import Any, Dict, Optional

# Внутренний словарь для хранения записей
_storage: Dict[str, Dict[str, Any]] = {}


def init_db() -> None:
    """Инициализировать/очистить хранилище."""
    _storage.clear()


def add_file(
    file_id: str, filename: str, metadata: Dict[str, Any], path: str, status: str
) -> None:
    """Сохранить информацию о файле."""
    _storage[file_id] = {
        "id": file_id,
        "filename": filename,
        "metadata": metadata,
        "path": path,
        "status": status,
    }


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Получить информацию о файле по ID."""
    return _storage.get(file_id)


def update_file(file_id: str, metadata: Dict[str, Any], path: str, status: str) -> None:
    """Обновить данные существующей записи."""
    if file_id in _storage:
        _storage[file_id].update(
            {"metadata": metadata, "path": path, "status": status}
        )


def delete_file(file_id: str) -> None:
    """Удалить запись о файле."""
    _storage.pop(file_id, None)


def list_files() -> list[Dict[str, Any]]:
    """Получить список всех файлов."""
    return list(_storage.values())

