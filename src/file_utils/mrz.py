from __future__ import annotations

import re
from datetime import datetime
from typing import Dict

__all__ = ["parse_mrz"]

# Регулярное выражение для MRZ паспортов (формат TD3)
MRZ_PASSPORT_RE = re.compile(
    r"P<(?P<country>[A-Z]{3})(?P<names>[A-Z<]+)\n"
    r"(?P<passport_number>[A-Z0-9<]{9})(?P<passport_check>\d)"
    r"[A-Z]{3}"
    r"(?P<birth_date>\d{6})(?P<birth_check>\d)"
    r"(?P<sex>[MF<])"
    r"(?P<expiration_date>\d{6})(?P<exp_check>\d)"
    r"[A-Z0-9<]+",
)


def _format_date(raw: str) -> str | None:
    """Преобразовать дату из формата YYMMDD в ISO YYYY-MM-DD."""
    if not re.fullmatch(r"\d{6}", raw):
        return None
    year = int(raw[0:2])
    month = int(raw[2:4])
    day = int(raw[4:6])
    # Примитивная эвристика определения века
    century = 1900 if year >= 50 else 2000
    try:
        dt = datetime(century + year, month, day)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_mrz(text: str) -> Dict[str, str | None]:
    """Извлечь основные поля из MRZ (Machine Readable Zone).

    Поддерживается стандартный формат паспортов (TD3).
    Возвращает словарь с ключами ``passport_number``, ``person``,
    ``date_of_birth`` и ``expiration_date``. Если MRZ не найден,
    возвращается пустой словарь.
    """

    # Упрощённая нормализация: приводим к верхнему регистру и убираем пробелы
    normalized = "\n".join(line.strip().replace(" ", "") for line in text.upper().splitlines())
    match = MRZ_PASSPORT_RE.search(normalized)
    if not match:
        return {}

    names = match.group("names")
    parts = names.split("<<")
    surname = parts[0].replace("<", " ").strip()
    given = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
    person = f"{given} {surname}".strip()

    passport_number = match.group("passport_number") + match.group("passport_check")
    passport_number = passport_number.replace("<", "")

    dob = _format_date(match.group("birth_date"))
    exp = _format_date(match.group("expiration_date"))

    return {
        "passport_number": passport_number or None,
        "person": person or None,
        "date_of_birth": dob,
        "expiration_date": exp,
    }
