from metadata_generation import generate_metadata, OpenRouterAnalyzer, RegexAnalyzer


def test_generate_metadata_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    text = "Total 123.45 on 2023-05-17"
    result = generate_metadata(text)
    assert result["date"] == "2023-05-17"
    assert result["amount"] == "123.45"
    assert result["category"] is None


def test_fallback_to_regex_on_analyze_error(monkeypatch):
    def fail(self, text):  # type: ignore[no-redef]
        raise RuntimeError("boom")

    monkeypatch.setattr(OpenRouterAnalyzer, "analyze", fail)

    called: dict[str, bool] = {}

    def fake_regex(self, text):  # type: ignore[no-redef]
        called["called"] = True
        return {"category": "regex"}

    monkeypatch.setattr(RegexAnalyzer, "analyze", fake_regex)

    analyzer = OpenRouterAnalyzer(api_key="test")
    result = generate_metadata("text", analyzer=analyzer)

    assert called.get("called")
    assert result["category"] == "regex"
