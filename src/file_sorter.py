from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple, Callable

from config import GENERAL_FOLDER_NAME
from utils.names import normalize_person_name

try:
    from unidecode import unidecode
except Exception:  # pragma: no cover
    unidecode = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _normalize_person_key(name: str | None) -> str:
    norm = normalize_person_name(name) or ""
    parts = norm.lower().split()
    return " ".join(sorted(parts))


def _normalize_category_key(name: str | None) -> str:
    return (name or "").strip().lower()


def build_folder_index(root_dir: str | Path) -> Dict[str, Dict[str, str]]:
    """Построить индекс существующих папок.

    Возвращает структуру ``{normalized_person: {normalized_category: path}}``.
    """
    root = Path(root_dir).resolve()
    index: Dict[str, Dict[str, str]] = {}
    if not root.exists():
        return index

    for person_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        person_key = _normalize_person_key(person_dir.name)
        categories: Dict[str, str] = {}
        for cat_dir in sorted(p for p in person_dir.iterdir() if p.is_dir()):
            cat_key = _normalize_category_key(cat_dir.name)
            categories[cat_key] = str(cat_dir.relative_to(root))
        index[person_key] = categories
    return index


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


def sanitize_dirname(name: str, replacement: str = "_") -> str:
    """Очистить имя каталога от недопустимых символов и ``..``.

    :param name: исходное имя каталога.
    :param replacement: символ для подстановки.
    :return: безопасное имя каталога.
    """
    # Сначала применяем те же правила, что и для имён файлов
    sanitized = sanitize_filename(name, replacement)
    # Удаляем попытки перехода к родительским каталогам
    sanitized = sanitized.replace("..", "")
    # Убираем ведущие символы подстановки
    if replacement:
        sanitized = sanitized.lstrip(replacement)
    return sanitized.strip()


def transliterate(name: str) -> str:
    """Преобразовать *name* в латиницу.

    Если библиотека ``unidecode`` недоступна, возвращает исходную строку.
    """
    if unidecode is None:
        return name
    return unidecode(name)


def get_folder_tree(
    root_dir: str | Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, str]]]:
    """Построить дерево папок и индекс существующих категорий.

    Каждый узел дерева имеет вид ``{"name", "path", "children", "files"}``,
    где ``files`` — список словарей ``{"name", "path"}`` для файлов в
    соответствующей директории.
    """
    root = Path(root_dir).resolve()

    def build(node: Path) -> Dict[str, Any]:
        children = [build(p) for p in sorted(node.iterdir()) if p.is_dir()]
        files = [
            {
                "name": f.name,
                "path": str(f.relative_to(root)),
            }
            for f in sorted(node.iterdir())
            if f.is_file()
        ]
        return {
            "name": node.name,
            "path": str(node.relative_to(root)),
            "children": children,
            "files": files,
        }

    if not root.exists():
        return [], {}

    tree = [build(p) for p in sorted(root.iterdir()) if p.is_dir()]
    index = build_folder_index(root)
    return tree, index


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
    :param confirm_callback: функция подтверждения создания каталогов. Ей передаётся
        список недостающих путей (относительно ``dest_root``), и она должна вернуть
        ``True``, если каталоги следует создать.
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
    person = normalize_person_name(metadata.get("person"))
    person = sanitize_dirname(person or "")
    if not person or not str(person).strip():
        person = GENERAL_FOLDER_NAME
    metadata["person"] = person
    dest_dir /= str(person)
    if not dest_dir.exists():
        missing.append(str(dest_dir.relative_to(base_dir)))

    # Затем category/subcategory, игнорируя совпадения с person
    for key in ("category", "subcategory"):
        value = metadata.get(key)
        if value:
            value = sanitize_dirname(str(value))
        if value and str(value).strip().lower() != str(person).strip().lower():
            dest_dir /= str(value)
            if not dest_dir.exists():
                missing.append(str(dest_dir.relative_to(base_dir)))
            metadata[key] = value
        else:
            metadata[key] = None

    # Затем issuer (если есть)
    issuer = metadata.get("issuer")
    if issuer:
        issuer = sanitize_dirname(str(issuer))
        if issuer:
            dest_dir /= str(issuer)
            if not dest_dir.exists():
                missing.append(str(dest_dir.relative_to(base_dir)))
            metadata["issuer"] = issuer
        else:
            metadata["issuer"] = None

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
        confirm_callback = lambda _paths: False  # type: ignore[assignment]

    # Создаём недостающие каталоги только при подтверждении
    if missing and needs_new_folder:
        confirmed = bool(confirm_callback(missing))
        if confirmed:
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except FileExistsError as exc:
                raise NotADirectoryError(
                    f"Cannot create directory '{exc.filename}'"
                ) from exc
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


def preview_destination(
    src_path: str | Path,
    metadata: Dict[str, Any],
    dest_root: str | Path,
    needs_new_folder: bool = False,
) -> Tuple[Path, List[str]]:
    """Рассчитать путь назначения без перемещения файла.

    Это удобная обёртка над :func:`place_file` с ``dry_run=True``.
    Возвращает путь к предполагаемому файлу и список недостающих каталогов.
    """

    dest, missing, _ = place_file(
        src_path,
        metadata,
        dest_root,
        dry_run=True,
        needs_new_folder=needs_new_folder,
        confirm_callback=None,
    )
    return dest, missing
