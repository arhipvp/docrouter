from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Body

from .. import db as database
from ..db import run_db
from services import openrouter
from services.openrouter import OpenRouterError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat/{file_id}")
async def chat(file_id: str, message: str = Body(..., embed=True)):
    """Простой чат с учётом текста файла."""
    record = await run_db(database.get_file, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    text = record.metadata.extracted_text or ""

    messages = [
        {"role": "system", "content": text},
        {"role": "user", "content": message},
    ]
    try:
        reply, tokens, cost = await openrouter.chat(messages)
    except OpenRouterError as exc:
        logger.exception("OpenRouter chat failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - сеть может быть недоступна
        logger.exception("OpenRouter chat failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("OpenRouter usage: tokens=%s, cost=%s", tokens, cost)

    await run_db(database.add_chat_message, file_id, "user", message)
    history = await run_db(
        database.add_chat_message, file_id, "assistant", reply, tokens=tokens, cost=cost
    )
    return {"response": reply, "chat_history": history}
