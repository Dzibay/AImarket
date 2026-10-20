"""Внутреннее API для бота: ответы из Telegram-темы → чат на сайте."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.security import require_bot
from app.support import (
    discard_images,
    message_error_code,
    post_staff_guest_message_from_telegram,
    post_staff_message_from_telegram,
)
from app.support_media import read_upload_images
from app.support_telegram import remember_topic, resolve_anchor, resolve_topic, support_telegram_chat_id

router = APIRouter(dependencies=[Depends(require_bot)], tags=["support-bot"])


class TelegramReplyIn(BaseModel):
    topic_id: int = Field(gt=0)
    body: str = Field(min_length=1, max_length=4000)
    anchor: str = Field(default="", max_length=4000)


@router.get("/support/telegram/config")
def telegram_config() -> dict:
    chat_id = support_telegram_chat_id()
    return {"chat_id": chat_id, "enabled": chat_id is not None}


def _deliver_telegram_reply(topic_id: int, body: str, anchor: str, images: list[dict]) -> dict:
    target = resolve_topic(topic_id)
    if target is None:
        target = resolve_anchor(anchor)
        if target is not None:
            remember_topic(target["kind"], target["id"], topic_id)
    if target is None:
        discard_images(images)
        raise HTTPException(status_code=404, detail="topic")
    try:
        if target["kind"] == "user":
            message = post_staff_message_from_telegram(target["id"], body, images)
        else:
            message = post_staff_guest_message_from_telegram(target["id"], body, images)
    except LookupError:
        discard_images(images)
        raise HTTPException(status_code=404, detail=target["kind"]) from None
    except ValueError as exc:
        discard_images(images)
        raise HTTPException(status_code=400, detail=message_error_code(exc)) from None
    return {"ok": True, "kind": target["kind"], "id": target["id"], "message": message}


@router.post("/support/telegram/reply")
def telegram_reply(body: TelegramReplyIn) -> dict:
    return _deliver_telegram_reply(body.topic_id, body.body, body.anchor, [])


@router.post("/support/telegram/reply/media")
async def telegram_reply_media(
    topic_id: int = Form(),
    body: str = Form(default=""),
    anchor: str = Form(default=""),
    files: list[UploadFile] | None = File(default=None),
) -> dict:
    if topic_id <= 0:
        raise HTTPException(status_code=400, detail="topic")
    try:
        images = await read_upload_images(files or [])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=message_error_code(exc)) from None
    return _deliver_telegram_reply(topic_id, body[:4000], anchor[:4000], images)
