from __future__ import annotations

import re
from typing import Optional

# Грубый список окончаний фамилий для распознавания
_SURNAME_ENDINGS = (
    "ов",
    "ова",
    "ев",
    "ева",
    "ёв",
    "ёва",
    "ин",
    "ина",
    "ын",
    "ына",
    "ий",
    "ый",
    "ая",
    "ко",
    "юк",
    "ич",
    "енко",
    "ский",
    "ская",
    "цкий",
    "цкая",
)


_NAME_SPLIT_RE = re.compile(r"[\s,]+")


def _looks_like_surname(part: str) -> bool:
    lower = part.lower()
    return any(lower.endswith(end) for end in _SURNAME_ENDINGS)


def normalize_person_name(name: Optional[str]) -> Optional[str]:
    """Привести ФИО к формату ``Фамилия Имя Отчество``.

    - Удаляет лишние запятые и пробелы.
    - Убирает повторяющиеся части.
    - Преобразует ``Имя Фамилия`` в ``Фамилия Имя`` при необходимости.
    - Каждую часть приводит к виду ``Title Case`` (поддерживает дефис).
    """
    if not name:
        return name

    parts = [p for p in _NAME_SPLIT_RE.split(name.strip()) if p]
    if not parts:
        return None

    # Удаляем дубли (регистр не важен)
    seen = set()
    unique_parts = []
    for part in parts:
        key = part.lower()
        if key not in seen:
            seen.add(key)
            unique_parts.append(part)
    parts = unique_parts

    if len(parts) == 2:
        first_surname = _looks_like_surname(parts[0])
        second_surname = _looks_like_surname(parts[1])
        if second_surname and not first_surname:
            parts = [parts[1], parts[0]]
    elif len(parts) == 3:
        if _looks_like_surname(parts[1]) and not _looks_like_surname(parts[0]):
            parts = [parts[1], parts[0], parts[2]]

    def _norm_word(word: str) -> str:
        return "-".join(w.capitalize() for w in word.split("-"))

    parts = [_norm_word(p) for p in parts]
    return " ".join(parts)


__all__ = ["normalize_person_name"]
