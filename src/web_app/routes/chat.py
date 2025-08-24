from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Body

from .. import db as database

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat/{file_id}")
async def chat(file_id: str, message: str = Body(..., embed=True)):
    """Простой чат с учётом текста файла."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    text = record.metadata.extracted_text or ""
    reply = f"Эхо: {message} | {text}".strip()

    database.add_chat_message(file_id, "user", message)
    history = database.add_chat_message(file_id, "assistant", reply)
    return {"response": reply, "chat_history": history}
