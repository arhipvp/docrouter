import pytest

from src.metadata_schema import validate_metadata


def test_validate_metadata_ok():
    data = {"result": "ok"}
    assert validate_metadata(data) == data


def test_validate_metadata_invalid():
    with pytest.raises(ValueError):
        validate_metadata({})
