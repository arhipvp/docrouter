from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Any
import os

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - fallback if PyYAML is unavailable
    yaml = None


def _read_env(env_path: Path) -> Dict[str, str]:
    """Parse a simple ``.env`` file into a dictionary."""
    data: Dict[str, str] = {}
    if not env_path.exists():
        return data
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


@lru_cache(maxsize=1)
def load_config() -> Dict[str, Any]:
    """Load configuration from ``config.yml`` and ``.env``.

    Values from ``.env`` override those from ``config.yml``. Results are
    cached, so subsequent calls do not re-read the files.
    """
    config_path_env = os.getenv("CONFIG_PATH")
    if config_path_env:
        config_path = Path(config_path_env)
    else:
        config_path = Path(__file__).resolve().parent.parent / "config.yml"

    env_path_env = os.getenv("ENV_PATH")
    env_path = Path(env_path_env) if env_path_env else config_path.parent / ".env"

    config: Dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            if yaml:
                data = yaml.safe_load(fh) or {}
            else:  # simple key: value parser
                data: Dict[str, Any] = {}
                for line in fh.read().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()
            if isinstance(data, dict):
                config.update(data)

    env_values = _read_env(env_path)
    config.update(env_values)

    return config
