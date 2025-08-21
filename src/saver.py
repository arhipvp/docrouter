from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict


def store_document(path: Path, metadata: Dict) -> Path:
    """Сохранить документ и его метаданные в архив.

    На основе полей ``категория``, ``подкатегория`` и ``человек``/``организация``
    формируется итоговый путь ``Архив/<Категория>/<Подкатегория>/<Человек или Организация>``.
    Файл копируется в полученный каталог, а JSON с метаданными сохраняется рядом
    с расширением ``.json``.

    Parameters
    ----------
    path:
        Путь к исходному файлу.
    metadata:
        Словарь с метаданными документа.

    Returns
    -------
    Path
        Путь к сохранённому файлу в архиве.
    """

    category = metadata.get("категория", "Unknown")
    subcategory = metadata.get("подкатегория", "Unknown")
    person_or_org = (
        metadata.get("человек")
        or metadata.get("организация")
        or metadata.get("человек/организация")
        or "Unknown"
    )

    dest_dir = Path("Архив") / category / subcategory / person_or_org
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / path.name
    shutil.copy2(path, dest_path)

    meta_path = dest_path.with_suffix(dest_path.suffix + ".json")
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return dest_path.resolve()
