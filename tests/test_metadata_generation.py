from metadata_generation import generate_metadata


def test_generate_metadata_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    text = "Total 123.45 on 2023-05-17"
    result = generate_metadata(text)
    assert result["date"] == "2023-05-17"
    assert result["amount"] == "123.45"
    assert result["category"] is None
