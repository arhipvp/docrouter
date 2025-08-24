from __future__ import annotations

"""Простейшее хранилище метаданных в памяти."""

from typing import Any, Dict, Optional, List

from models import FileRecord, Metadata

# Внутренний словарь для хранения записей
_storage: Dict[str, FileRecord] = {}


def init_db() -> None:
    """Инициализировать/очистить хранилище."""
    _storage.clear()


def add_file(
    file_id: str,
    filename: str,
    metadata: Metadata,
    path: str,
    status: str,
    prompt: Any | None = None,
    raw_response: Any | None = None,
    missing: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    translated_text: str | None = None,
    translation_lang: str | None = None,
    embedding: list[float] | None = None,
    suggested_path: str | None = None,
) -> None:
    """Сохранить информацию о файле."""
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
        chat_history=[],
        sources=sources,
        embedding=embedding,
        suggested_path=suggested_path,
    )
    _storage[file_id] = record


def get_file(file_id: str) -> Optional[FileRecord]:
    """Получить информацию о файле по ID."""
    return _storage.get(file_id)


def get_details(file_id: str) -> Optional[FileRecord]:
    """Вернуть полную запись без фильтрации полей."""
    return _storage.get(file_id)


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
    embedding: list[float] | None = None,
    suggested_path: str | None = None,
) -> None:
    """Обновить данные существующей записи."""
    record = _storage.get(file_id)
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
    if embedding is not None:
        record.embedding = embedding
    if suggested_path is not None:
        record.suggested_path = suggested_path


def delete_file(file_id: str) -> None:
    """Удалить запись о файле."""
    _storage.pop(file_id, None)


def list_files() -> list[FileRecord]:
    """Получить список всех файлов."""
    return list(_storage.values())


def add_chat_message(file_id: str, role: str, message: str) -> List[Dict[str, str]]:
    """Добавить запись в историю чата."""
    record = _storage.get(file_id)
    if record is None:
        return []
    history: List[Dict[str, str]] = record.chat_history
    history.append({"role": role, "message": message})
    return history


def get_chat_history(file_id: str) -> List[Dict[str, str]]:
    """Получить историю чата по файлу."""
    record = _storage.get(file_id)
    if record is None:
        return []
    return record.chat_history
