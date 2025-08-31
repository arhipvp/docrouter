from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple, Callable

from config import GENERAL_FOLDER_NAME

try:
    from unidecode import unidecode
except Exception:  # pragma: no cover
    unidecode = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Запрещённые для имён файлов символы (Windows-совместимо)
INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')
# Паттерн даты YYYY-MM-DD для удаления из suggested_name
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Заменяет недопустимые символы в имени файла.

    :param name: исходное имя (без расширения).
    :param replacement: символ для подстановки.
    :return: скорректированное имя.
    """
    return INVALID_CHARS_PATTERN.sub(replacement, name)


def transliterate(name: str) -> str:
    """Преобразовать *name* в латиницу.

    Если библиотека ``unidecode`` недоступна, возвращает исходную строку.
    """
    if unidecode is None:
        return name
    return unidecode(name)


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
    needs_new_folder: bool = False,
    confirm_callback: Callable[[List[str]], bool] | None = None,
) -> Tuple[Path, List[str], bool]:
    """Переместить файл в структуру папок на основе *metadata*.

    Структура: ``<dest_root>/<person>/<category>/<subcategory>/<issuer>/<DATE>__<NAME>.<ext>``.
    Рядом с файлом сохраняется ``.json`` с теми же метаданными.

    Возвращает кортеж ``(dest_file, missing, confirmed)``, где:
      - ``dest_file`` — предполагаемый/фактический путь к файлу,
      - ``missing`` — список отсутствующих каталогов (пути относительно ``dest_root``),
      - ``confirmed`` — было ли создано новое дерево каталогов.

    Поведение:
      - При ``dry_run=True`` ничего не создаётся и не перемещается — только расчёт путей.
      - Каталоги создаются лишь при ``needs_new_folder=True`` и положительном ответе
        ``confirm_callback``.

    :param src_path: путь к исходному файлу.
    :param metadata: словарь с ключами: ``category``, ``subcategory``, ``person``, ``issuer``,
                     ``date`` (YYYY-MM-DD), ``suggested_name``.
    :param dest_root: корень архива.
    :param dry_run: «сухой прогон» без изменений на диске.
    :param needs_new_folder: требуется ли создание новой директории.
    :param confirm_callback: функция подтверждения создания каталогов.
    :return: (путь к файлу назначения, список отсутствующих каталогов, подтверждение).
    """
    src = Path(src_path)
    base_dir = Path(dest_root)
    if base_dir.exists():
        if not base_dir.is_dir():
            raise NotADirectoryError(
                f"Destination root exists and is not a directory: {base_dir}"
            )
    else:  # Создаём корень архива, если его нет
        base_dir.mkdir(parents=True, exist_ok=True)

    ext = src.suffix
    raw_name = metadata.get("suggested_name") or src.stem
    raw_name = DATE_PATTERN.sub("", str(raw_name)).strip(" _-")
    name = sanitize_filename(raw_name)
    metadata["suggested_name"] = name
    translit = sanitize_filename(transliterate(name))
    metadata["suggested_name_translit"] = translit
    date = metadata.get("date") or "unknown-date"

    base_new_name = f"{date}__{name}"
    base_translit = f"{date}__{translit}"

    dest_dir = base_dir
    missing: List[str] = []

    # Сначала person (или общий)
    person = metadata.get("person")
    if not person or not str(person).strip():
        person = GENERAL_FOLDER_NAME
    metadata["person"] = person
    dest_dir /= str(person)
    if not dest_dir.exists():
        missing.append(str(dest_dir.relative_to(base_dir)))

    # Затем category/subcategory
    for key in ("category", "subcategory"):
        value = metadata.get(key)
        if value:
            dest_dir /= str(value)
            if not dest_dir.exists():
                missing.append(str(dest_dir.relative_to(base_dir)))

    # Затем issuer (если есть)
    issuer = metadata.get("issuer")
    if issuer:
        dest_dir /= str(issuer)
        if not dest_dir.exists():
            missing.append(str(dest_dir.relative_to(base_dir)))

    def _unique_path() -> tuple[Path, str]:
        dest = dest_dir / f"{base_new_name}{ext}"
        translit_name = f"{base_translit}{ext}"
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{base_new_name}_{counter}{ext}"
            translit_name = f"{base_translit}_{counter}{ext}"
            counter += 1
        return dest, translit_name

    dest_file, translit_name = _unique_path()
    metadata["new_name_translit"] = translit_name
    json_file = dest_file.with_suffix(dest_file.suffix + ".json")

    confirmed = False

    # Сухой прогон — только расчёт
    if dry_run:
        logger.info("Would move %s -> %s", src, dest_file)
        logger.info("Would write metadata JSON to %s", json_file)
        return dest_file, missing, confirmed

    if confirm_callback is None:
        confirm_callback = lambda *_: False  # type: ignore[assignment]

    # Создаём недостающие каталоги только при подтверждении
    if missing and needs_new_folder and confirm_callback(missing):
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError as exc:
            raise NotADirectoryError(
                f"Cannot create directory '{exc.filename}'"
            ) from exc
        confirmed = True
        missing = []

    # Если каталоги всё ещё отсутствуют — выходим
    if missing:
        logger.debug("Missing directories (no create): %s", missing)
        return dest_file, missing, confirmed

    # Проверяем ещё раз перед переносом на случай гонок
    dest_file, translit_name = _unique_path()
    metadata["new_name_translit"] = translit_name
    json_file = dest_file.with_suffix(dest_file.suffix + ".json")

    # Перемещаем файл
    shutil.move(str(src), str(dest_file))
    logger.info("Moved %s -> %s", src, dest_file)

    # Пишем метаданные
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.debug("Wrote metadata to %s", json_file)

    return dest_file, missing, confirmed
