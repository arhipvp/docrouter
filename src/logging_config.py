from __future__ import annotations

import logging
from pathlib import Path


FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: str, log_file: Path | None) -> None:
    """Configure logging for console and optional file output.

    Parameters
    ----------
    level:
        Log level name (e.g., "INFO", "DEBUG").
    log_file:
        If provided, logs are also written to this file.
    """
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=FORMAT,
        handlers=handlers,
        force=True,
    )
