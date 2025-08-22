from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Заменяет недопустимые символы в имени файла.

    :param name: исходное имя (без расширения).
    :param replacement: символ для подстановки.
    :return: скорректированное имя.
    """
    return INVALID_CHARS_PATTERN.sub(replacement, name)


def get_folder_tree(root_dir: str | Path) -> List[Dict[str, Any]]:
    """Построить список словарей с деревом папок, начиная с *root_dir*.

    Каждый узел содержит поля ``name`` и ``path`` (относительный путь от
    ``root_dir``) и список ``children``. Пустые каталоги имеют пустой список
    ``children``.

    :param root_dir: корневая директория, которую нужно просканировать.
    :return: список словарей, описывающих структуру папок.
    """
    root = Path(root_dir).resolve()

    def build(node: Path) -> Dict[str, Any]:
        children = [build(p) for p in sorted(node.iterdir()) if p.is_dir()]
        return {
            "name": node.name,
            "path": str(node.relative_to(root)),
            "children": children,
        }

    if not root.exists():
        return []

    return [build(p) for p in sorted(root.iterdir()) if p.is_dir()]


def place_file(
    src_path: str | Path,
    metadata: Dict[str, Any],
    dest_root: str | Path,
    dry_run: bool = False,
    create_missing: bool = True,
) -> Tuple[Path, List[str]]:
    """Перемещает файл в структуру папок на основе метаданных.

    Создаёт вложенные папки (категория/подкатегория/issuer),
    переименовывает файл вида ``DATE__NAME.ext`` и сохраняет рядом JSON
    с теми же метаданными.

    Возвращает кортеж ``(dest_file, missing)``, где:
      - ``dest_file`` — предполагаемый/фактический путь к файлу,
      - ``missing`` — список отсутствующих каталогов (относительно ``dest_root``).

    Поведение:
      - При ``dry_run=True`` ничего не создаёт и не перемещает, только расчёт путей.
      - При ``create_missing=False`` и наличии отсутствующих каталогов файл не переносится.
      - Если каталоги существуют (или были созданы при ``create_missing=True``), файл переносится и пишется JSON.
    """
    src = Path(src_path)
    ext = src.suffix
    name = metadata.get("suggested_name") or src.stem
    name = sanitize_filename(name)
    date = metadata.get("date", "unknown-date")

    new_name = f"{date}__{name}{ext}"

    base_dir = Path(dest_root)
    dest_dir = base_dir
    missing: List[str] = []
    for key in ("category", "subcategory", "issuer"):
        value = metadata.get(key)
        if value:
            dest_dir /= value
            if not dest_dir.exists():
                # сохраняем отсутствующую директорию как путь относительно корня
                missing.append(str(dest_dir.relative_to(base_dir)))

    dest_file = dest_dir / new_name
    json_file = dest_file.with_suffix(dest_file.suffix + ".json")

    # Сухой прогон — только расчёт
    if dry_run:
        logger.info("Would move %s -> %s", src, dest_file)
        logger.info("Would write metadata JSON to %s", json_file)
        return dest_file, missing

    # Если нельзя создавать каталоги и они отсутствуют — выходим
    if missing and not create_missing:
        logger.debug("Missing directories (no create): %s", missing)
        return dest_file, missing

    # Создаём недостающие каталоги при необходимости
    if missing and create_missing:
        dest_dir.mkdir(parents=True, exist_ok=True)

    # Перемещаем файл
    shutil.move(str(src), dest_file)
    logger.info("Moved %s -> %s", src, dest_file)

    # Пишем метаданные
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.debug("Wrote metadata to %s", json_file)

    return dest_file, []
