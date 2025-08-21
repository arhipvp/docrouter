import os
import time
import json
import requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
EXPECTED_FIELDS = [
    "category",
    "subcategory",
    "date",
    "issuer",
    "person",
    "document_type",
    "amount",
    "tags",
    "suggested_filename",
    "note",
]

def fetch_metadata_from_llm(text, max_retries=3):
    """Send text to OpenRouter LLM and parse structured JSON response.

    Retries the request if the model returns invalid JSON.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openrouter/llama3-8b")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    system_prompt = (
        "You extract metadata from documents. Respond with JSON containing the keys: "
        "category, subcategory, date, issuer, person, document_type, amount, tags, "
        "suggested_filename, note. Use empty strings or an empty list where data is missing."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    }

    for attempt in range(max_retries):
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        try:
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                parts = content.split("```", 2)
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
            data = json.loads(content)
            for field in EXPECTED_FIELDS:
                if field not in data:
                    data[field] = [] if field == "tags" else ""
            return data
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
