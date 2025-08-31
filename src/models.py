from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class Metadata(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    issuer: Optional[str] = None
    person: Optional[str] = None
    doc_type: Optional[str] = None
    date: Optional[str] = None
    date_of_birth: Optional[str] = None
    expiration_date: Optional[str] = None
    passport_number: Optional[str] = None
    amount: Optional[str] = None
    tags: List[str] = []
    tags_ru: List[str] = []
    tags_en: List[str] = []
    suggested_filename: Optional[str] = None
    description: Optional[str] = None
    needs_new_folder: bool = False
    extracted_text: Optional[str] = None
    language: Optional[str] = None
    suggested_name: Optional[str] = None
    suggested_name_translit: Optional[str] = None
    new_name_translit: Optional[str] = None


class FileRecord(BaseModel):
    id: str
    filename: str
    metadata: Metadata
    tags_ru: List[str] = []
    tags_en: List[str] = []
    person: Optional[str] = None
    date_of_birth: Optional[str] = None
    expiration_date: Optional[str] = None
    passport_number: Optional[str] = None
    path: str
    status: str
    prompt: Any | None = None
    raw_response: Any | None = None
    missing: List[str] = []
    translated_text: Optional[str] = None
    translation_lang: Optional[str] = None
    chat_history: List[dict[str, Any]] = []
    sources: Optional[List[str]] = None
    suggested_path: Optional[str] = None
    created_path: Optional[str] = None
    confirmed: bool = False


class UploadResponse(BaseModel):
    id: str
    status: str
    filename: Optional[str] = None
    metadata: Optional[Metadata] = None
    tags_ru: List[str] = []
    tags_en: List[str] = []
    path: Optional[str] = None
    missing: List[str] = []
    prompt: Any | None = None
    raw_response: Any | None = None
    sources: Optional[List[str]] = None
    suggested_path: Optional[str] = None
