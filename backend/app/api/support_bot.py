"""Внутреннее API для бота: ответы из Telegram-темы → чат на сайте."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import require_bot
from app.support import (
    post_staff_guest_message_from_telegram,
    post_staff_message_from_telegram,
)
from app.support_telegram import resolve_topic, support_telegram_chat_id

router = APIRouter(dependencies=[Depends(require_bot)], tags=["support-bot"])


class TelegramReplyIn(BaseModel):
    topic_id: int = Field(gt=0)
    body: str = Field(min_length=1, max_length=4000)


@router.get("/support/telegram/config")
def telegram_config() -> dict:
    chat_id = support_telegram_chat_id()
    return {"chat_id": chat_id, "enabled": chat_id is not None}


@router.post("/support/telegram/reply")
def telegram_reply(body: TelegramReplyIn) -> dict:
    target = resolve_topic(body.topic_id)
    if target is None:
        raise HTTPException(status_code=404, detail="topic")
    try:
        if target["kind"] == "user":
            message = post_staff_message_from_telegram(target["id"], body.body)
        else:
            message = post_staff_guest_message_from_telegram(target["id"], body.body)
    except LookupError:
        raise HTTPException(status_code=404, detail=target["kind"]) from None
    except ValueError as exc:
        code = str(exc) if str(exc) in {"message", "long"} else "message"
        raise HTTPException(status_code=400, detail=code) from None
    return {"ok": True, "kind": target["kind"], "id": target["id"], "message": message}
