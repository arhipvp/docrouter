from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Body

from .. import db as database
from services import openrouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat/{file_id}")
async def chat(file_id: str, message: str = Body(..., embed=True)):
    """Простой чат с учётом текста файла."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    text = record.metadata.extracted_text or ""

    messages = [
        {"role": "system", "content": text},
        {"role": "user", "content": message},
    ]
    try:
        reply, tokens, cost = await openrouter.chat(messages)
    except Exception as exc:  # pragma: no cover - сеть может быть недоступна
        logger.exception("OpenRouter chat failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("OpenRouter usage: tokens=%s, cost=%s", tokens, cost)

    database.add_chat_message(file_id, "user", message)
    history = database.add_chat_message(
        file_id, "assistant", reply, tokens=tokens, cost=cost
    )
    return {"response": reply, "chat_history": history}
