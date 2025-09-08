"""Package for DocRouter CLI and submodules."""

from importlib import import_module as _import_module
from pathlib import Path as _Path
import sys as _sys

# Allow using top-level modules under the ``docrouter`` namespace lazily.
__path__.append(str(_Path(__file__).resolve().parent.parent))

_SUPPORTED_MODULES = {
    "config",
    "error_handling",
    "file_sorter",
    "metadata_generation",
    "models",
    "ocr_pipeline",
    "prompt_templates",
    "file_utils",
    "utils",
    "services",
    "plugins",
    "web_app",
    "logging_config",
}


def __getattr__(name: str):  # pragma: no cover - thin wrapper
    """Dynamically import supported modules on first access."""
    if name in _SUPPORTED_MODULES:
        module = _import_module(name)
        _sys.modules[f"{__name__}.{name}"] = module
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = ["main"]
