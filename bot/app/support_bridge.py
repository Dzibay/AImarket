"""Ответы операторов из Telegram-темы форума → чат поддержки на сайте."""

from __future__ import annotations

import logging
import time

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from app.backend import BackendError, support_telegram_config, support_telegram_reply

log = logging.getLogger("app.support_bridge")
router = Router(name="support-bridge")

_cached_chat_id: int | None = None
_cached_at = 0.0
_CACHE_TTL = 60.0


async def _support_chat_id() -> int | None:
    global _cached_chat_id, _cached_at
    now = time.monotonic()
    if now - _cached_at < _CACHE_TTL and _cached_at > 0:
        return _cached_chat_id
    try:
        data = await support_telegram_config()
    except BackendError as exc:
        log.warning("не удалось получить config поддержки: %s", exc)
        return _cached_chat_id
    raw = data.get("chat_id")
    _cached_chat_id = int(raw) if raw is not None else None
    _cached_at = now
    return _cached_chat_id


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.message_thread_id)
async def support_topic_message(message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    chat_id = await _support_chat_id()
    if chat_id is None or message.chat.id != chat_id:
        return

    text = (message.text or message.caption or "").strip()
    if not text:
        try:
            await message.reply("На сайт уходит только текст. Пришлите ответ сообщением.")
        except Exception:
            pass
        return

    topic_id = int(message.message_thread_id)
    try:
        await support_telegram_reply(topic_id, text)
    except BackendError as exc:
        if exc.status == 404:
            try:
                await message.reply("Эта тема не привязана к диалогу на сайте.")
            except Exception:
                pass
            return
        log.warning("ответ в поддержку не принят (%s): %s", exc.status, exc.detail)
        try:
            await message.reply("Не удалось отправить на сайт. Попробуйте ещё раз.")
        except Exception:
            pass
