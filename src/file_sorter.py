from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Заменяет недопустимые символы в имени файла.

    :param name: исходное имя (без расширения).
    :param replacement: символ для подстановки.
    :return: скорректированное имя.
    """
    return INVALID_CHARS_PATTERN.sub(replacement, name)


def get_folder_tree(root_dir: str | Path) -> Dict[str, Any]:
    """Построить словарь с деревом папок, начиная с *root_dir*.

    В результирующем словаре ключами являются имена директорий, а
    значениями — такие же словари для вложенных директорий.

    :param root_dir: корневая директория, которую нужно просканировать.
    :return: вложенный словарь, описывающий структуру папок.
    """
    root = Path(root_dir)
    tree: Dict[str, Any] = {}
    if not root.exists():
        return tree
    for path in sorted(root.iterdir()):
        if path.is_dir():
            tree[path.name] = get_folder_tree(path)
    return tree


def place_file(src_path: str | Path, metadata: Dict[str, Any], dest_root: str | Path, dry_run: bool = False) -> Path:
    """Перемещает файл в структуру папок на основе метаданных.

    Создаёт вложенные папки (категория/подкатегория/issuer),
    переименовывает файл вида ``DATE__NAME.ext`` и сохраняет рядом JSON
    с теми же метаданными.

    При ``dry_run=True`` только выводит предполагаемые действия.

    Возвращает путь, по которому файл будет или был размещён.
    """

    src = Path(src_path)
    ext = src.suffix
    name = metadata.get("suggested_name") or src.stem
    name = sanitize_filename(name)
    date = metadata.get("date", "unknown-date")

    new_name = f"{date}__{name}{ext}"

    dest_dir = Path(dest_root)
    for key in ("category", "subcategory", "issuer"):
        value = metadata.get(key)
        if value:
            dest_dir /= value

    dest_file = dest_dir / new_name
    json_file = dest_file.with_suffix(dest_file.suffix + ".json")

    if dry_run:
        logger.info("Would move %s -> %s", src, dest_file)
        logger.info("Would write metadata JSON to %s", json_file)
        return dest_file

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dest_file)
    logger.info("Moved %s -> %s", src, dest_file)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.debug("Wrote metadata to %s", json_file)

    return dest_file
