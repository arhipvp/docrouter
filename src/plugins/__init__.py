"""Utility to auto-load plugin modules from this package."""
from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def load_plugins() -> None:
    """Import all modules in this package to register plugins."""
    package_dir = Path(__file__).parent
    for module_info in iter_modules([str(package_dir)]):
        # Skip packages or private modules
        if module_info.ispkg or module_info.name.startswith("_"):
            continue
        module_name = f"{__name__}.{module_info.name}"
        try:
            import_module(module_name)
        except Exception as exc:  # pragma: no cover - plugin errors shouldn't crash
            logger.error("Failed to load plugin %s: %s", module_name, exc)
