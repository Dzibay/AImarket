"""Ответы операторов из Telegram-темы форума → чат поддержки на сайте."""

from __future__ import annotations

import logging
import time
from io import BytesIO

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
    images = await _images_from_message(message)
    had_image = bool(message.photo) or (
        message.document is not None and (message.document.mime_type or "").startswith("image/")
    )
    if had_image and not images:
        try:
            await message.reply("Не удалось прочитать фото. Пришлите его ещё раз.")
        except Exception:
            pass
        if not text:
            return
    if not text and not images:
        try:
            await message.reply("На сайт уходят текст и фото. Пришлите сообщение или картинку.")
        except Exception:
            pass
        return

    reply = message.reply_to_message
    anchor = ""
    if reply is not None:
        anchor = reply.text or reply.caption or ""
    try:
        await support_telegram_reply(topic_id, text, anchor, images)
        log.info("ответ из темы %s отправлен на сайт", topic_id)
    except BackendError as exc:
        if exc.status == 404:
            try:
                await message.reply("Эта тема не привязана к диалогу на сайте.")
            except Exception:
                pass
            return
        log.warning("ответ в поддержку не принят (%s): %s", exc.status, exc.detail)
        notice = {
            "too-big": "Фото больше 8 МБ. Сожмите его и пришлите снова.",
            "too-many": "За раз можно отправить не больше 4 фото.",
            "image": "Нужен файл JPEG, PNG, WEBP или GIF.",
            "message": "На сайт уходят текст и фото. Пришлите сообщение или картинку.",
        }.get(exc.detail, "Не удалось отправить на сайт. Попробуйте ещё раз.")
        try:
            await message.reply(notice)
        except Exception:
            pass


async def _images_from_message(message: Message) -> list[tuple[str, bytes, str]]:
    found: list[tuple[str, bytes, str]] = []
    if message.photo:
        item = await _download(message, message.photo[-1], "photo.jpg", "image/jpeg")
        if item is not None:
            found.append(item)
    document = message.document
    mime = (document.mime_type or "") if document is not None else ""
    if document is not None and mime.startswith("image/"):
        item = await _download(message, document, document.file_name or "image", mime)
        if item is not None:
            found.append(item)
    return found


async def _download(message: Message, file_obj, name: str, mime: str) -> tuple[str, bytes, str] | None:
    try:
        buffer = BytesIO()
        await message.bot.download(file_obj, destination=buffer)
    except Exception as exc:
        log.warning("не удалось скачать вложение из темы: %s", exc)
        return None
    data = buffer.getvalue()
    if not data:
        return None
    return name, data, mime
