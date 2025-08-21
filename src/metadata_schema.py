from __future__ import annotations

from pydantic import BaseModel, ValidationError


class Metadata(BaseModel):
    """Схема метаданных, возвращаемых LLM."""

    result: str


def validate_metadata(data: dict) -> dict:
    """Проверяет словарь с метаданными и возвращает нормализованный результат.

    :param data: словарь, полученный от LLM
    :raises ValueError: если данные не соответствуют схеме
    :return: нормализованные метаданные
    """
    try:
        metadata = Metadata(**data)
    except ValidationError as exc:  # noqa: F841
        raise ValueError("invalid metadata") from exc
    return metadata.dict()
