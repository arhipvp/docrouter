from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from src import error_handler, extractor, llm_client, saver, scanner

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process documents in a folder")
    parser.add_argument("input_dir", type=Path, help="Path to input directory")
    parser.add_argument("--dry-run", action="store_true", help="Do not save results")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    return parser.parse_args(argv)


def process_documents(input_dir: Path, dry_run: bool) -> tuple[int, int, int]:
    documents = scanner.list_documents(input_dir)
    total = len(documents)
    successes = 0
    failures = 0

    for path in documents:
        logger.info("Processing %s", path)
        try:
            text = extractor.extract_text(path)
            metadata = llm_client.analyze_text(text)
            if dry_run:
                logger.info("Dry-run: would save %s", path)
            else:
                saver.store_document(path, metadata)
            successes += 1
        except Exception as exc:  # pragma: no cover - exercised via tests
            error_handler.handle_error(path, exc)
            failures += 1

    return total, successes, failures


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    if args.dry_run:
        os.environ["DRY_RUN"] = "1"
    else:
        os.environ.pop("DRY_RUN", None)

    total, successes, failures = process_documents(args.input_dir, args.dry_run)
    logger.info(
        "Processed %d files: %d succeeded, %d failed", total, successes, failures
    )
    print(f"Processed {total} files: {successes} succeeded, {failures} failed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
