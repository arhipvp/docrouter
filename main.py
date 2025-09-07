"""Точка входа для запуска DocRouter как скрипта.

Запускает сервер FastAPI, используя основную функцию пакета ``docrouter``.

При запуске из исходников модуль ``docrouter`` может быть недоступен в
``sys.path``. Чтобы «python main.py" работал без предварительной установки
пакета, добавляем каталог ``src`` в путь поиска модулей.
"""
from __future__ import annotations

import sys
from pathlib import Path


# Добавляем каталог ``src`` рядом с этим файлом в ``sys.path`` при необходимости
ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from docrouter.main import main

if __name__ == "__main__":
    main()
