import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from path_builder import build_target_path


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yml"
    cfg.write_text(
        """
        categories:
          - Платежи
          - Отчёты
        subcategories:
          - Коммунальные
          - Годовой
        persons:
          - Иван
        organizations:
          - ООО Ромашка
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("DOCROUTER_CONFIG", str(cfg))
    return cfg


def test_build_target_path_normalizes_values(config_file):
    metadata = {
        "категория": "платежи",
        "подкатегория": "коммунальные",
        "человек/организация": "иван",
    }
    result = build_target_path(metadata)
    expected = Path("Архив") / "Платежи" / "Коммунальные" / "Иван"
    assert result == expected


def test_build_target_path_unknown_category_returns_unsorted(config_file):
    metadata = {
        "категория": "неизвестная",
        "подкатегория": "коммунальные",
        "человек": "иван",
    }
    assert build_target_path(metadata) == Path("Unsorted")


def test_build_target_path_missing_field_returns_unsorted(config_file):
    metadata = {
        "категория": "платежи",
        "человек": "иван",
    }
    assert build_target_path(metadata) == Path("Unsorted")


def test_build_target_path_unknown_person_returns_unsorted(config_file):
    metadata = {
        "категория": "платежи",
        "подкатегория": "коммунальные",
        "человек": "петр",
    }
    assert build_target_path(metadata) == Path("Unsorted")
