import asyncio
import json
from typing import Any, Dict

import pytest

from metadata_generation import (
    generate_metadata,
    OpenRouterError,
    MetadataAnalyzer,
)
from models import Metadata


class DummyAnalyzer(MetadataAnalyzer):
    async def analyze(
        self, text: str, folder_tree: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return {"prompt": None, "raw_response": None, "metadata": {}}


def test_generate_metadata_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(OpenRouterError):
        asyncio.run(generate_metadata("text"))


def test_folder_tree_in_prompt(monkeypatch):
    captured: dict[str, str] = {}

    class DummyResponse:
        status_code = 200
        text = "{}"

        def raise_for_status(self) -> None:
            pass

        def json(self) -> Dict[str, Any]:  # type: ignore[override]
            return {
                "choices": [
                    {"message": {"content": json.dumps({"needs_new_folder": True})}}
                ]
            }

    async def fake_post(self, url, json=None, headers=None, **kwargs):  # type: ignore[no-redef]
        captured["prompt"] = json["messages"][0]["content"]
        return DummyResponse()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("metadata_generation.OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("metadata_generation.httpx.AsyncClient.post", fake_post)

    tree = [
        {
            "name": "Финансы",
            "path": "Финансы",
            "children": [{"name": "Банки", "path": "Финансы/Банки", "children": []}],
        }
    ]
    result = asyncio.run(generate_metadata("text", folder_tree=tree))
    instruction = "Если ни одна папка не подходит, предложи новую category/subcategory."
    tree_json = json.dumps(tree, ensure_ascii=False)
    assert tree_json in captured["prompt"]
    assert tree_json in result["prompt"]
    assert instruction in captured["prompt"]
    assert instruction in result["prompt"]
    assert result["metadata"].needs_new_folder is True


def test_response_format_in_extra_body(monkeypatch):
    captured: dict[str, Any] = {}

    class DummyResponse:
        status_code = 200
        text = "{}"

        def raise_for_status(self) -> None:
            pass

        def json(self) -> Dict[str, Any]:  # type: ignore[override]
            return {"choices": [{"message": {"content": json.dumps({})}}]}

    async def fake_post(self, url, json=None, headers=None, **kwargs):  # type: ignore[no-redef]
        captured["json"] = json
        return DummyResponse()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("metadata_generation.OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("metadata_generation.httpx.AsyncClient.post", fake_post)

    asyncio.run(generate_metadata("text"))
    assert "extra_body" in captured["json"]
    assert captured["json"]["extra_body"] == {"response_format": {"type": "json_object"}}


def test_multilanguage_tags_parsing(monkeypatch):
    class DummyResponse:
        status_code = 200
        text = json.dumps(
            {
                "choices": [
                    {"message": {"content": json.dumps({"tags": []})}}
                ]
            }
        )

        def raise_for_status(self) -> None:
            pass

        def json(self) -> Dict[str, Any]:  # type: ignore[override]
            data = {
                "tags_ru": ["тег1", "тег2"],
                "tags_en": ["tag1", "tag2"],
            }
            return {"choices": [{"message": {"content": json.dumps(data)}}]}

    async def fake_post(self, url, json=None, headers=None, **kwargs):  # type: ignore[no-redef]
        return DummyResponse()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("metadata_generation.OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("metadata_generation.httpx.AsyncClient.post", fake_post)

    result = asyncio.run(generate_metadata("text"))
    meta: Metadata = result["metadata"]
    assert meta.tags_ru == ["тег1", "тег2"]
    assert meta.tags_en == ["tag1", "tag2"]


def test_generate_metadata_parses_mrz():
    text = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C<3UTO7408122F1204159ZE184226B<<<<<<<<<10"
    )
    result = asyncio.run(generate_metadata(text, analyzer=DummyAnalyzer()))
    meta = result["metadata"]
    assert meta.person == "ANNA MARIA ERIKSSON"
    assert meta.date_of_birth == "1974-08-12"
    assert meta.expiration_date == "2012-04-15"
    assert meta.passport_number == "L898902C3"
