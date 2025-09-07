"""Package for DocRouter CLI and submodules."""
from importlib import import_module as _import_module
import sys as _sys

# Expose top-level modules under the docrouter namespace for compatibility
for _name in [
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
]:
    _sys.modules[f"{__name__}.{_name}"] = _import_module(_name)

__all__ = ["main"]
