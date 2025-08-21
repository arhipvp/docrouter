from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure modules from the src package are importable when running from repo root
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from config import LOG_LEVEL  # type: ignore
from logging_config import setup_logging  # type: ignore
from docrouter import process_directory  # type: ignore

logger = logging.getLogger(__name__)


def main() -> None:
    """Command-line entry point for DocRouter."""
    parser = argparse.ArgumentParser(description="DocRouter entry point")
    parser.add_argument("input_dir", help="Directory with input files")
    parser.add_argument("--output", default="Archive", help="Destination root directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without moving files")
    parser.add_argument("--log-file", type=Path, default=None, help="Optional log file path")
    args = parser.parse_args()

    setup_logging(LOG_LEVEL, args.log_file)
    logger.info("Processing directory %s", args.input_dir)
    process_directory(args.input_dir, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
