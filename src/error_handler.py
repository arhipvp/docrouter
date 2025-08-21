import os
from pathlib import Path
import shutil

import yaml

from logger import get_logger

logger = get_logger(__name__)


def _str_to_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y"}


def is_dry_run() -> bool:
    """Determine whether the application runs in dry-run mode.

    Priority is given to the ``DRY_RUN`` environment variable. If it is not
    set, the configuration file is consulted. The path to the configuration
    file can be overridden via the ``CONFIG_PATH`` environment variable.
    """
    env_val = os.getenv("DRY_RUN")
    if env_val is not None:
        return _str_to_bool(env_val)

    config_path_env = os.getenv("CONFIG_PATH")
    if config_path_env:
        config_path = Path(config_path_env)
    else:
        config_path = Path(__file__).resolve().parent.parent / "config.yml"

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            dry_value = data.get("dry_run")
            if isinstance(dry_value, bool):
                return dry_value
            if isinstance(dry_value, str):
                return _str_to_bool(dry_value)
        except Exception as exc:  # pragma: no cover - logging of config issues
            logger.warning("Failed to read config file %s: %s", config_path, exc)
    return False


def handle_error(path: Path, error: Exception) -> None:
    """Handle processing errors.

    The file ``path`` will be moved into an ``Unsorted`` subdirectory next to
    its original location. In ``dry-run`` mode, only logging is performed.
    """
    logger.error("Error processing %s: %s", path, error)
    destination_dir = path.parent / "Unsorted"
    destination = destination_dir / path.name

    if is_dry_run():
        logger.info("Dry-run: would move %s to %s", path, destination)
        return

    try:
        destination_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
        logger.info("Moved %s to %s", path, destination)
    except Exception as exc:  # pragma: no cover - secondary errors are rare
        logger.error("Failed to move %s to %s: %s", path, destination, exc)
