import json
import logging
import shutil
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)


def handle_error(file_path: str | Path, exception: Exception) -> None:
    """Log *exception*, move *file_path* to ``Unsorted`` and write JSON with details.

    The JSON is stored under ``errors/<filename>.json`` where ``<filename>`` is the
    original file name (including extension).
    """
    src = Path(file_path)
    logger.error("Ошибка при обработке %s: %s", src, exception)

    # Перемещаем файл в Unsorted/
    unsorted_dir = Path("Unsorted")
    unsorted_dir.mkdir(exist_ok=True)
    dest = unsorted_dir / src.name
    if src.exists():
        shutil.move(str(src), dest)

    # Сохраняем сведения об ошибке
    errors_dir = Path("errors")
    errors_dir.mkdir(exist_ok=True)
    error_info = {
        "file": src.name,
        "error": str(exception),
        "traceback": traceback.format_exc(),
    }
    error_file = errors_dir / f"{src.name}.json"
    with open(error_file, "w", encoding="utf-8") as f:
        json.dump(error_info, f, ensure_ascii=False, indent=2)
