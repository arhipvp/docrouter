from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional

import yaml


def _load_config() -> Dict:
    """Load configuration from YAML file.

    The path to the configuration file can be overridden via the
    ``DOCROUTER_CONFIG`` environment variable.
    """
    config_path = os.getenv("DOCROUTER_CONFIG", "config.yml")
    with open(Path(config_path), encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _normalize(value: Optional[str], options: Iterable[str]) -> Optional[str]:
    """Return canonical form of ``value`` if it exists in ``options``.

    Matching is case-insensitive. If ``value`` is ``None`` or not found,
    ``None`` is returned.
    """
    if not value:
        return None
    mapping = {opt.casefold(): opt for opt in options}
    return mapping.get(value.strip().casefold())


def build_target_path(metadata: Dict) -> Path:
    """Construct destination path based on ``metadata``.

    The result has the form ``Архив/<Категория>/<Подкатегория>/<Человек или Организация>``.
    If any of the required fields is missing or unknown, ``Unsorted`` is
    returned instead.
    """
    config = _load_config()
    categories = config.get("categories", [])
    subcategories = config.get("subcategories", [])
    persons = config.get("persons", [])
    organizations = config.get("organizations", [])

    category = _normalize(metadata.get("категория"), categories)
    subcategory = _normalize(metadata.get("подкатегория"), subcategories)

    person = _normalize(metadata.get("человек"), persons)
    organization = _normalize(metadata.get("организация"), organizations)
    combined = persons + organizations
    human_or_org = metadata.get("человек/организация")
    human_or_org = _normalize(human_or_org, combined) if human_or_org else None
    person_or_org = human_or_org or person or organization

    if not all([category, subcategory, person_or_org]):
        return Path("Unsorted")

    return Path("Архив") / category / subcategory / person_or_org
