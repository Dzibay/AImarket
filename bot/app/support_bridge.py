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

# Сообщения админов с выключенной подписью приходят от этого служебного бота.
_GROUP_ANONYMOUS_BOT_ID = 1087968824

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


def _is_operator(message: Message) -> bool:
    user = message.from_user
    if user is not None and not user.is_bot:
        return True
    # Анонимный админ пишет от GroupAnonymousBot или без автора, но от имени группы.
    # Сообщения самого бота (пересылка с сайта) сюда не входят.
    if user is not None and user.id == _GROUP_ANONYMOUS_BOT_ID:
        return True
    sender = message.sender_chat
    if user is None and sender is not None and message.chat is not None:
        return sender.id == message.chat.id
    return False


def _topic_id(message: Message) -> int | None:
    if message.message_thread_id:
        return int(message.message_thread_id)
    reply = message.reply_to_message
    if reply is not None and reply.message_thread_id:
        return int(reply.message_thread_id)
    return None


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def support_group_message(message: Message) -> None:
    if not _is_operator(message):
        return
    if (
        message.forum_topic_created
        or message.forum_topic_edited
        or message.forum_topic_closed
        or message.forum_topic_reopened
    ):
        return
    chat_id = await _support_chat_id()
    if chat_id is None or message.chat.id != chat_id:
        return

    # General / вне темы — на сайт не отправляем.
    topic_id = _topic_id(message)
    if not topic_id:
        text = (message.text or message.caption or "").strip()
        if text:
            log.info("сообщение в чате поддержки без темы, пропуск chat=%s", message.chat.id)
        return

    text = (message.text or message.caption or "").strip()
    if not text:
        try:
            await message.reply("На сайт уходит только текст. Пришлите ответ сообщением.")
        except Exception:
            pass
        return

    reply = message.reply_to_message
    anchor = ""
    if reply is not None:
        anchor = reply.text or reply.caption or ""
    try:
        await support_telegram_reply(topic_id, text, anchor)
        log.info("ответ из темы %s отправлен на сайт", topic_id)
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
