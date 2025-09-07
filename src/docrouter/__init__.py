"""Package namespace for DocRouter.

This module re-exports top-level modules so they can be imported via
``docrouter`` namespace, e.g. ``from docrouter.web_app.server import app``.
"""

from importlib import import_module
import sys as _sys

# Modules and packages to expose under the ``docrouter`` namespace.
_modules = [
    "config",
    "logging_config",
    "web_app",
]

__all__ = list(_modules)

for _name in _modules:
    _module = import_module(_name)
    _sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module
