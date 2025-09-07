import asyncio
import json
from typing import Any, Dict

import pytest

from metadata_generation import generate_metadata, MetadataAnalyzer
from file_sorter import build_folder_index
from services.openrouter import OpenRouterError
from models import Metadata


class DummyAnalyzer(MetadataAnalyzer):
    async def analyze(
        self,
        text: str,
        folder_tree: Dict[str, Any] | None = None,
        folder_index: Dict[str, Any] | None = None,
        file_info: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {"prompt": None, "raw_response": None, "metadata": {}}


def test_generate_metadata_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(OpenRouterError):
        asyncio.run(generate_metadata("text"))


def test_prompt_includes_context(monkeypatch):
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

    tree = [{"name": "Финансы", "children": [{"name": "Банки", "children": []}]}]
    index = {"иванов иван": {"финансы": "Иванов Иван/Финансы"}}
    file_info = {"name": "invoice", "extension": ".pdf", "size": 100, "type": "pdf"}
    result = asyncio.run(
        generate_metadata(
            "text", folder_tree=tree, folder_index=index, file_info=file_info
        )
    )
    prompt = captured["prompt"]
    tree_json = json.dumps(tree, ensure_ascii=False)
    index_json = json.dumps(index, ensure_ascii=False)
    instruction_part1 = "Если ни одна папка не подходит, предложи новую category/subcategory."
    instruction_part2 = (
        "Выбирай person/category строго из Existing folders index, если совпадение найдено; needs_new_folder=true только при полном отсутствии."
    )
    assert tree_json in prompt
    assert index_json in prompt
    assert file_info["name"] in prompt
    assert file_info["extension"] in prompt
    assert str(file_info["size"]) in prompt
    assert file_info["type"] in prompt
    assert "contracts" in prompt
    assert instruction_part1 in prompt
    assert instruction_part2 in prompt
    assert tree_json in result["prompt"]
    assert index_json in result["prompt"]
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
    assert "response_format" in captured["json"]
    assert captured["json"]["response_format"] == {"type": "json_object"}


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
                "tags": ["base"],
                "tags_ru": ["тег1", "тег2"],
                "tags_en": ["tag1", "tag2"],
                "category": "Категория",
                "subcategory": "Подкатегория",
                "doc_type": "Тип",
                "issuer": "Организация",
                "person": "Иван Иванов",
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
    expected = {
        "base",
        "тег1",
        "тег2",
        "tag1",
        "tag2",
        "Категория",
        "Подкатегория",
        "Тип",
        "Организация",
        "Иванов Иван",
    }
    assert expected.issubset(set(meta.tags))


def test_generate_metadata_parses_mrz():
    text = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C<3UTO7408122F1204159ZE184226B<<<<<<<<<10"
    )
    result = asyncio.run(generate_metadata(text, analyzer=DummyAnalyzer()))
    meta = result["metadata"]
    assert meta.person == "Anna Maria Eriksson"
    assert meta.date_of_birth == "1974-08-12"
    assert meta.expiration_date == "2012-04-15"
    assert meta.passport_number == "L898902C3"


class DummyFilenameAnalyzer(MetadataAnalyzer):
    async def analyze(
        self,
        text: str,
        folder_tree: Dict[str, Any] | None = None,
        folder_index: Dict[str, Any] | None = None,
        file_info: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "prompt": None,
            "raw_response": None,
            "metadata": {
                "suggested_filename": "invoice.pdf",
                "counterparty": "ACME",
                "document_number": "42",
                "due_date": "2024-12-31",
                "currency": "EUR",
            },
        }


def test_generate_metadata_extracts_suggested_name():
    result = asyncio.run(
        generate_metadata("text", analyzer=DummyFilenameAnalyzer())
    )
    meta: Metadata = result["metadata"]
    assert meta.suggested_filename == "invoice.pdf"
    assert meta.suggested_name == "invoice"
    assert meta.counterparty == "ACME"
    assert meta.document_number == "42"
    assert meta.due_date == "2024-12-31"
    assert meta.currency == "EUR"


def test_generate_metadata_parses_military_id_date():
    text = "Военный билет\nДата выдачи: 15.04.2020"
    result = asyncio.run(generate_metadata(text, analyzer=DummyAnalyzer()))
    meta: Metadata = result["metadata"]
    assert meta.date == "2020-04-15"


def test_folder_index_reuses_existing_folder(tmp_path):
    (tmp_path / "BONCH-OSMOLOVSKAIA, Natalia" / "Taxes").mkdir(parents=True)
    index = build_folder_index(tmp_path)

    class Analyzer(MetadataAnalyzer):
        async def analyze(
            self,
            text: str,
            folder_tree: Dict[str, Any] | None = None,
            folder_index: Dict[str, Any] | None = None,
            file_info: Dict[str, Any] | None = None,
        ) -> Dict[str, Any]:
            return {
                "prompt": None,
                "raw_response": None,
                "metadata": {
                    "person": "Natalia Bonch-Osmolovskaia",
                    "category": "Taxes",
                    "needs_new_folder": True,
                },
            }

    result = asyncio.run(
        generate_metadata("text", analyzer=Analyzer(), folder_index=index)
    )
    meta: Metadata = result["metadata"]
    assert meta.person == "BONCH-OSMOLOVSKAIA, Natalia"
    assert meta.category == "Taxes"
    assert meta.needs_new_folder is False


class InvalidAnalyzer(MetadataAnalyzer):
    async def analyze(
        self,
        text: str,
        folder_tree: Dict[str, Any] | None = None,
        folder_index: Dict[str, Any] | None = None,
        file_info: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {"prompt": None, "raw_response": None, "metadata": ["not", "a", "dict"]}


def test_generate_metadata_handles_invalid_metadata():
    result = asyncio.run(generate_metadata("text", analyzer=InvalidAnalyzer()))
    meta: Metadata = result["metadata"]
    assert meta.category is None
    assert meta.tags == []


class ListAnalyzer(MetadataAnalyzer):
    async def analyze(
        self,
        text: str,
        folder_tree: Dict[str, Any] | None = None,
        folder_index: Dict[str, Any] | None = None,
        file_info: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "prompt": None,
            "raw_response": None,
            "metadata": [{"category": "Health", "tags": ["a"]}],
        }


def test_generate_metadata_accepts_list_of_dicts():
    result = asyncio.run(generate_metadata("text", analyzer=ListAnalyzer()))
    meta: Metadata = result["metadata"]
    assert meta.category == "Health"
    assert set(meta.tags) == {"a", "Health"}
