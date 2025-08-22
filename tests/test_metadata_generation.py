import json
from typing import Any, Dict

from metadata_generation import generate_metadata, OpenRouterAnalyzer, RegexAnalyzer


def test_generate_metadata_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    text = "Total 123.45 on 2023-05-17"
    result = generate_metadata(text)
    meta = result["metadata"]
    assert meta["date"] == "2023-05-17"
    assert meta["amount"] == "123.45"
    assert meta["category"] is None
    assert meta["needs_new_folder"] is False
    assert meta["tags_ru"] == []
    assert meta["tags_en"] == []
    assert result["prompt"] is None
    assert result["raw_response"] is None


def test_fallback_to_regex_on_analyze_error(monkeypatch):
    def fail(self, text, folder_tree=None):  # type: ignore[no-redef]
        raise RuntimeError("boom")

    monkeypatch.setattr(OpenRouterAnalyzer, "analyze", fail)

    called: dict[str, bool] = {}

    def fake_regex(self, text, folder_tree=None):  # type: ignore[no-redef]
        called["called"] = True
        return {"prompt": None, "raw_response": None, "metadata": {"category": "regex"}}

    monkeypatch.setattr(RegexAnalyzer, "analyze", fake_regex)

    analyzer = OpenRouterAnalyzer(api_key="test")
    result = generate_metadata("text", analyzer=analyzer)

    assert called.get("called")
    assert result["metadata"]["category"] == "regex"
    assert result["metadata"]["needs_new_folder"] is False


def test_folder_tree_in_prompt(monkeypatch):
    captured: dict[str, str] = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> Dict[str, Any]:  # type: ignore[override]
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"needs_new_folder": True})
                        }
                    }
                ]
            }

    def fake_post(url, json, headers, timeout):  # type: ignore[no-redef]
        captured["prompt"] = json["messages"][0]["content"]
        return DummyResponse()

    monkeypatch.setattr("metadata_generation.requests.post", fake_post)

    analyzer = OpenRouterAnalyzer(api_key="test")
    tree = [
        {
            "name": "Финансы",
            "path": "Финансы",
            "children": [
                {"name": "Банки", "path": "Финансы/Банки", "children": []}
            ],
        }
    ]
    result = generate_metadata("text", analyzer=analyzer, folder_tree=tree)
    instruction = "Если ни одна папка не подходит, предложи новую category/subcategory."
    tree_json = json.dumps(tree, ensure_ascii=False)
    assert tree_json in captured["prompt"]
    assert tree_json in result["prompt"]
    assert instruction in captured["prompt"]
    assert instruction in result["prompt"]
    assert result["metadata"]["needs_new_folder"] is True


def test_multilanguage_tags_parsing(monkeypatch):
    class DummyResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> Dict[str, Any]:  # type: ignore[override]
            data = {
                "tags_ru": ["тег1", "тег2"],
                "tags_en": ["tag1", "tag2"],
            }
            return {"choices": [{"message": {"content": json.dumps(data)}}]}

    def fake_post(url, json, headers, timeout):  # type: ignore[no-redef]
        return DummyResponse()

    monkeypatch.setattr("metadata_generation.requests.post", fake_post)

    analyzer = OpenRouterAnalyzer(api_key="test")
    result = generate_metadata("text", analyzer=analyzer)
    meta = result["metadata"]
    assert meta["tags_ru"] == ["тег1", "тег2"]
    assert meta["tags_en"] == ["tag1", "tag2"]


def test_generate_metadata_parses_mrz():
    text = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C<3UTO7408122F1204159ZE184226B<<<<<<<<<10"
    )
    result = generate_metadata(text, analyzer=RegexAnalyzer())
    meta = result["metadata"]
    assert meta["person"] == "ANNA MARIA ERIKSSON"
    assert meta["date_of_birth"] == "1974-08-12"
    assert meta["expiration_date"] == "2012-04-15"
    assert meta["passport_number"] == "L898902C3"
