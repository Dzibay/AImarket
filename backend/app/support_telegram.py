"""Мост сайта ↔ Telegram: темы форума в группе поддержки."""

from __future__ import annotations

import html
import json
import logging
import threading
import urllib.error
import urllib.request

from app.config import settings
from app.db import pool
from app.settings_store import get_setting

log = logging.getLogger("app.support_telegram")


def support_telegram_chat_id() -> int | None:
    raw = get_setting("support_telegram_chat_id").strip().replace(" ", "")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        log.warning("некорректный support_telegram_chat_id: %s", raw)
        return None


def forward_user_message(*, user_id: int | None = None, guest_id: int | None = None, body: str) -> None:
    """Асинхронно создаёт/находит тему и пишет туда сообщение пользователя."""
    if not body.strip():
        return
    if (user_id is None) == (guest_id is None):
        return
    threading.Thread(
        target=_forward_safe,
        kwargs={"user_id": user_id, "guest_id": guest_id, "body": body, "as_staff": False},
        name="support-tg-user",
        daemon=True,
    ).start()


def forward_staff_message(*, user_id: int | None = None, guest_id: int | None = None, body: str) -> None:
    """Дублирует ответ из админки сайта в тему Telegram (если тема уже есть)."""
    if not body.strip():
        return
    if (user_id is None) == (guest_id is None):
        return
    threading.Thread(
        target=_forward_safe,
        kwargs={"user_id": user_id, "guest_id": guest_id, "body": body, "as_staff": True},
        name="support-tg-staff",
        daemon=True,
    ).start()


def _forward_safe(*, user_id: int | None, guest_id: int | None, body: str, as_staff: bool) -> None:
    try:
        _forward(user_id=user_id, guest_id=guest_id, body=body, as_staff=as_staff)
    except Exception:
        log.exception("не удалось отправить сообщение поддержки в Telegram")


def _forward(*, user_id: int | None, guest_id: int | None, body: str, as_staff: bool) -> None:
    token = settings.telegram_bot_token.strip()
    chat_id = support_telegram_chat_id()
    if not token or chat_id is None:
        return

    with pool.connection() as conn:
        if user_id is not None:
            row = conn.execute(
                """
                SELECT id, email, username, first_name, support_telegram_topic_id AS topic_id
                FROM users WHERE id = %s
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                return
            topic_id = row["topic_id"]
            label = _user_label(row)
            kind = "user"
            ref_id = int(row["id"])
        else:
            row = conn.execute(
                """
                SELECT id, telegram_topic_id AS topic_id
                FROM support_guests WHERE id = %s
                """,
                (guest_id,),
            ).fetchone()
            if row is None:
                return
            topic_id = row["topic_id"]
            label = f"Гость #{int(row['id'])}"
            kind = "guest"
            ref_id = int(row["id"])

        if topic_id is None:
            if as_staff:
                return
            topic_id = _create_topic(token, chat_id, label)
            if topic_id is None:
                return
            if kind == "user":
                conn.execute(
                    "UPDATE users SET support_telegram_topic_id = %s WHERE id = %s",
                    (topic_id, ref_id),
                )
            else:
                conn.execute(
                    "UPDATE support_guests SET telegram_topic_id = %s WHERE id = %s",
                    (topic_id, ref_id),
                )
            header = f"<b>{html.escape(label)}</b>\n<code>{kind}:{ref_id}</code>\n\n"
            text = header + html.escape(body)
        else:
            prefix = "<i>Ответ с сайта</i>\n" if as_staff else ""
            text = prefix + html.escape(body)

    _send_topic_message(token, chat_id, int(topic_id), text)


def _user_label(row: dict) -> str:
    email = (row.get("email") or "").strip()
    if email:
        return email[:64]
    name = (row.get("first_name") or "").strip()
    user = (row.get("username") or "").strip()
    if name and user:
        return f"{name} @{user}"[:64]
    if user:
        return f"@{user}"[:64]
    if name:
        return name[:64]
    return f"Клиент #{int(row['id'])}"


def _create_topic(token: str, chat_id: int, name: str) -> int | None:
    title = (name or "Поддержка")[:128]
    try:
        payload = _telegram_call(
            token,
            "createForumTopic",
            {"chat_id": str(chat_id), "name": title},
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("createForumTopic failed: %s", exc)
        return None
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return None
    topic = result.get("message_thread_id")
    return int(topic) if topic is not None else None


def _send_topic_message(token: str, chat_id: int, topic_id: int, text: str) -> None:
    # Telegram лимит ~4096 символов.
    chunk = text if len(text) <= 4000 else text[:3990] + "…"
    try:
        _telegram_call(
            token,
            "sendMessage",
            {
                "chat_id": str(chat_id),
                "message_thread_id": str(topic_id),
                "text": chunk,
                "parse_mode": "HTML",
            },
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("sendMessage в тему %s failed: %s", topic_id, exc)


def _telegram_call(token: str, method: str, fields: dict[str, str]) -> dict:
    boundary = "----aimarket-support"
    body = bytearray()
    for name, value in fields.items():
        body.extend(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode()
        )
    body.extend(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "aimarket",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode())
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise urllib.error.URLError(str(payload)[:300])
    return payload


def resolve_topic(topic_id: int) -> dict | None:
    """Возвращает {kind, id} для темы форума или None."""
    with pool.connection() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE support_telegram_topic_id = %s",
            (topic_id,),
        ).fetchone()
        if user is not None:
            return {"kind": "user", "id": int(user["id"])}
        guest = conn.execute(
            "SELECT id FROM support_guests WHERE telegram_topic_id = %s",
            (topic_id,),
        ).fetchone()
        if guest is not None:
            return {"kind": "guest", "id": int(guest["id"])}
    return None


def rename_topic_after_guest_claim(*, user_id: int, topic_id: int, guest_id: int) -> None:
    """После слияния гостя: переименовать тему в email и отметить, что диалог был гостевым."""
    threading.Thread(
        target=_rename_after_claim_safe,
        kwargs={"user_id": user_id, "topic_id": topic_id, "guest_id": guest_id},
        name="support-tg-rename",
        daemon=True,
    ).start()


def _rename_after_claim_safe(*, user_id: int, topic_id: int, guest_id: int) -> None:
    try:
        _rename_after_claim(user_id=user_id, topic_id=topic_id, guest_id=guest_id)
    except Exception:
        log.exception("не удалось переименовать тему после слияния гостя")


def _rename_after_claim(*, user_id: int, topic_id: int, guest_id: int) -> None:
    token = settings.telegram_bot_token.strip()
    chat_id = support_telegram_chat_id()
    if not token or chat_id is None:
        return
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id, email, username, first_name FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    if row is None:
        return
    label = _user_label(row)
    # 🔄 — диалог начинался как гостевой, потом привязан к аккаунту.
    title = f"🔄 {label}"[:128]
    try:
        _telegram_call(
            token,
            "editForumTopic",
            {
                "chat_id": str(chat_id),
                "message_thread_id": str(topic_id),
                "name": title,
            },
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("editForumTopic %s failed: %s", topic_id, exc)
        return
    note = (
        f"🔄 Гостевой диалог <b>Гость #{guest_id}</b> привязан к аккаунту "
        f"<b>{html.escape(label)}</b> <code>user:{user_id}</code>."
    )
    _send_topic_message(token, chat_id, topic_id, note)
