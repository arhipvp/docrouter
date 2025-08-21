from __future__ import annotations

import logging
from pathlib import Path

from config import LOG_LEVEL
from logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging(LOG_LEVEL, None)


def log_exception(exc: Exception, *, file: Path | None = None) -> None:
    """Log an exception with optional file context."""
    if file:
        logger.error("Error processing %s", file, exc_info=exc)
    else:
        logger.error("Unhandled exception", exc_info=exc)
