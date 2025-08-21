from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config import LOG_LEVEL
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="DocRouter entry point")
    parser.add_argument("input_dir", nargs="?", default=".", help="Directory with input files")
    parser.add_argument("--log-file", type=Path, default=None, help="Optional log file path")
    args = parser.parse_args()

    setup_logging(LOG_LEVEL, args.log_file)
    logger.info("Processing directory %s", args.input_dir)


if __name__ == "__main__":
    main()
