import os
from pydantic import BaseModel

class Settings(BaseModel):
    data_dir: str = os.getenv("DATA_DIR","/data")
    inbox_dir: str = os.getenv("INBOX_DIR","/data/Inbox")
    out_dir: str = os.getenv("OUT_DIR","/data/Out")
    ann_dir: str = os.getenv("ANN_DIR","/data/Annotations")
    tmp_dir: str = os.getenv("TMP_DIR","/data/Tmp")
    ocr_lang: str = os.getenv("OCR_LANG","deu+eng+rus")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL","openai/gpt-5-nano-2025-08-07")
    translate_provider: str = os.getenv("TRANSLATE_PROVIDER","off")  # deepl|argos|off
    deepl_api_key: str | None = os.getenv("DEEPL_API_KEY")

settings = Settings()
