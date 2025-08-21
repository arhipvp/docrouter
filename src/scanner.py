from __future__ import annotations

from pathlib import Path


def _is_hidden_or_temp(part: str) -> bool:
    """Check whether a path component is hidden or temporary."""
    return (
        part.startswith('.')
        or part.startswith('~')
        or part.endswith('~')
        or part.startswith('#')
        or part.endswith('#')
    )


def list_documents(input_dir: Path) -> list[Path]:
    """Recursively list document files in ``input_dir``.

    Hidden and temporary files or directories are skipped.
    """
    result: list[Path] = []
    for path in input_dir.rglob('*'):
        if not path.is_file():
            continue
        parts = path.relative_to(input_dir).parts
        if any(_is_hidden_or_temp(part) for part in parts):
            continue
        result.append(path)
    return sorted(result)
