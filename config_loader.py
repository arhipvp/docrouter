import os
from dotenv import load_dotenv
import yaml


def load_config(config_path: str = "config.yml"):
    """Load application configuration from a YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_openrouter_settings():
    """Load OpenRouter API key and model from environment variables."""
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL")
    return {"api_key": api_key, "model": model}
