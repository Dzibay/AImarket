"""Мост сайта ↔ Telegram: темы форума в группе поддержки."""

from __future__ import annotations

import html
import json
import logging
import re
import threading
import urllib.error
import urllib.request

from psycopg.errors import UniqueViolation

from app.config import settings
from app.db import pool
from app.settings_store import get_setting

log = logging.getLogger("app.support_telegram")

_HISTORY_LIMIT = 200
_ANCHOR_RE = re.compile(r"\b(user|guest):(\d+)\b")


def support_telegram_chat_id() -> int | None:
    raw = get_setting("support_telegram_chat_id").strip().replace(" ", "")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        log.warning("некорректный support_telegram_chat_id: %s", raw)
        return None


def forward_user_message(
    *,
    user_id: int | None = None,
    guest_id: int | None = None,
    body: str,
    message_id: int,
) -> None:
    """Сообщение клиента с сайта → тема Telegram."""
    _schedule_sync(user_id=user_id, guest_id=guest_id, body=body, message_id=message_id)


def forward_staff_message(
    *,
    user_id: int | None = None,
    guest_id: int | None = None,
    body: str,
    message_id: int,
) -> None:
    """Ответ из админки сайта → та же тема Telegram. Тему создаёт, если её ещё нет."""
    _schedule_sync(user_id=user_id, guest_id=guest_id, body=body, message_id=message_id)


def notify_telegram_message(
    *,
    user_id: int | None = None,
    guest_id: int | None = None,
    message_id: int,
) -> None:
    """Ответ уже есть в теме. Досылает в неё пропущенные сообщения сайта и сдвигает курсор."""
    _schedule_sync(user_id=user_id, guest_id=guest_id, body="", message_id=message_id)


def _schedule_sync(
    *,
    user_id: int | None,
    guest_id: int | None,
    body: str,
    message_id: int,
) -> None:
    if message_id <= 0:
        return
    if (user_id is None) == (guest_id is None):
        return
    threading.Thread(
        target=_sync_safe,
        kwargs={
            "user_id": user_id,
            "guest_id": guest_id,
            "body": body,
            "message_id": message_id,
        },
        name="support-tg-sync",
        daemon=True,
    ).start()


def _sync_safe(*, user_id: int | None, guest_id: int | None, body: str, message_id: int) -> None:
    try:
        _sync_out(user_id=user_id, guest_id=guest_id, body=body, message_id=message_id)
    except Exception:
        log.exception("не удалось синхронизировать чат поддержки с Telegram")


def _lock_key(kind: str, ref_id: int) -> int:
    base = 1_000_000_000_000 if kind == "user" else 2_000_000_000_000
    return base + ref_id


def _sync_out(*, user_id: int | None, guest_id: int | None, body: str, message_id: int) -> None:
    token = settings.telegram_bot_token.strip()
    chat_id = support_telegram_chat_id()
    if not token or chat_id is None:
        return
    kind = "user" if user_id is not None else "guest"
    ref_id = int(user_id if user_id is not None else guest_id)
    key = _lock_key(kind, ref_id)
    with pool.connection() as conn:
        # Снимается вместе с commit/rollback, поэтому соединение в пуле не остаётся с замком.
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (key,))
        _sync_locked(
            conn,
            token=token,
            chat_id=chat_id,
            kind=kind,
            ref_id=ref_id,
            body=body,
            message_id=message_id,
        )


def _sync_locked(
    conn,
    *,
    token: str,
    chat_id: int,
    kind: str,
    ref_id: int,
    body: str,
    message_id: int,
) -> None:
    state = _load_state(conn, kind, ref_id)
    if state is None:
        return
    topic_id = state["topic_id"]
    synced = state["synced_id"]
    if topic_id is None:
        _open_topic(conn, token, chat_id, state, kind, ref_id, message_id)
        return

    if synced is None:
        # Старая тема: не выгружаем всю историю повторно.
        # Берём это сообщение и то, что пришло за последние секунды, чтобы параллельная
        # отправка не перескочила курсор и не потеряла реплику.
        rows = _recent_untracked(conn, kind, ref_id, message_id)
        if not rows:
            return
        sent, error = _publish(token, chat_id, int(topic_id), state, rows, intro=False)
        if error and _thread_missing(error):
            _recreate_topic(conn, token, chat_id, state, kind, ref_id, message_id)
            return
        if error:
            if sent is not None:
                _save_synced(conn, kind, ref_id, sent)
            return
        _save_synced(conn, kind, ref_id, max(message_id, sent or 0))
        return

    rows = _pending_messages(conn, kind, ref_id, after_id=int(synced))
    sent, error = _publish(
        token,
        chat_id,
        int(topic_id),
        state,
        rows,
        intro=int(synced) == 0,
    )
    if error and _thread_missing(error):
        _recreate_topic(conn, token, chat_id, state, kind, ref_id, message_id)
        return
    if error:
        if sent is not None and sent > int(synced):
            _save_synced(conn, kind, ref_id, sent)
        return
    cursor = sent if sent is not None else int(synced)
    if cursor > int(synced):
        _save_synced(conn, kind, ref_id, cursor)


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


def _load_state(conn, kind: str, ref_id: int) -> dict | None:
    if kind == "user":
        row = conn.execute(
            """
            SELECT id, email, username, first_name,
                   support_telegram_topic_id AS topic_id,
                   support_telegram_synced_id AS synced_id
            FROM users WHERE id = %s
            """,
            (ref_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "kind": "user",
            "ref_id": int(row["id"]),
            "label": _user_label(row),
            "topic_id": int(row["topic_id"]) if row["topic_id"] is not None else None,
            "synced_id": int(row["synced_id"]) if row["synced_id"] is not None else None,
        }
    row = conn.execute(
        """
        SELECT id, telegram_topic_id AS topic_id, telegram_synced_id AS synced_id
        FROM support_guests WHERE id = %s
        """,
        (ref_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "kind": "guest",
        "ref_id": int(row["id"]),
        "label": f"Гость #{int(row['id'])}",
        "topic_id": int(row["topic_id"]) if row["topic_id"] is not None else None,
        "synced_id": int(row["synced_id"]) if row["synced_id"] is not None else None,
    }


def _recent_untracked(conn, kind: str, ref_id: int, message_id: int) -> list:
    column = "user_id" if kind == "user" else "guest_id"
    return conn.execute(
        f"""
        SELECT id, author_kind, source, body
        FROM support_messages
        WHERE {column} = %s
          AND source <> 'telegram'
          AND (id = %s OR created_at > NOW() - INTERVAL '45 seconds')
        ORDER BY created_at ASC, id ASC
        LIMIT %s
        """,
        (ref_id, message_id, _HISTORY_LIMIT),
    ).fetchall()


def _pending_messages(conn, kind: str, ref_id: int, *, after_id: int) -> list:
    column = "user_id" if kind == "user" else "guest_id"
    return conn.execute(
        f"""
        SELECT id, author_kind, source, body
        FROM support_messages
        WHERE {column} = %s AND id > %s
        ORDER BY created_at ASC, id ASC
        LIMIT %s
        """,
        (ref_id, after_id, _HISTORY_LIMIT),
    ).fetchall()


def _save_topic(conn, kind: str, ref_id: int, topic_id: int | None) -> None:
    if kind == "user":
        conn.execute(
            "UPDATE users SET support_telegram_topic_id = %s WHERE id = %s",
            (topic_id, ref_id),
        )
        return
    conn.execute(
        "UPDATE support_guests SET telegram_topic_id = %s WHERE id = %s",
        (topic_id, ref_id),
    )


def _save_synced(conn, kind: str, ref_id: int, synced_id: int | None) -> None:
    if kind == "user":
        conn.execute(
            "UPDATE users SET support_telegram_synced_id = %s WHERE id = %s",
            (synced_id, ref_id),
        )
        return
    conn.execute(
        "UPDATE support_guests SET telegram_synced_id = %s WHERE id = %s",
        (synced_id, ref_id),
    )


def _open_topic(conn, token: str, chat_id: int, state: dict, kind: str, ref_id: int, message_id: int) -> None:
    topic_id = _create_topic(token, chat_id, state["label"])
    if topic_id is None:
        return
    _save_topic(conn, kind, ref_id, topic_id)
    # 0 отличает новую тему от старой: при сбое история дошлётся целиком, а не одним сообщением.
    _save_synced(conn, kind, ref_id, 0)
    rows = _pending_messages(conn, kind, ref_id, after_id=0)
    sent, _error = _publish(token, chat_id, topic_id, state, rows, intro=True)
    if sent is not None:
        _save_synced(conn, kind, ref_id, sent)
    elif not rows:
        _save_synced(conn, kind, ref_id, message_id)


def _recreate_topic(
    conn,
    token: str,
    chat_id: int,
    state: dict,
    kind: str,
    ref_id: int,
    message_id: int,
) -> None:
    _save_topic(conn, kind, ref_id, None)
    _save_synced(conn, kind, ref_id, None)
    _open_topic(conn, token, chat_id, state, kind, ref_id, message_id)


def _thread_missing(detail: str) -> bool:
    text = (detail or "").lower()
    return "message thread not found" in text or "thread not found" in text


def _publish(
    token: str,
    chat_id: int,
    topic_id: int,
    state: dict,
    rows: list,
    *,
    intro: bool,
) -> tuple[int | None, str]:
    """Пишет строки в тему. Возвращает id последней обработанной строки и текст ошибки."""
    if intro:
        header = (
            f"<b>{html.escape(state['label'])}</b>\n"
            f"<code>{state['kind']}:{state['ref_id']}</code>"
        )
        error = _send_topic_message(token, chat_id, topic_id, header)
        if error:
            return None, error
    last_sent: int | None = None
    for row in rows:
        # В живой теме ответ оператора уже лежит сообщением Telegram — повторно его не шлём.
        if not intro and row.get("source") == "telegram":
            last_sent = int(row["id"])
            continue
        error = _send_topic_message(
            token,
            chat_id,
            topic_id,
            _format_line(row["author_kind"], row["body"]),
        )
        if error:
            return last_sent, error
        last_sent = int(row["id"])
    return last_sent, ""


def _format_line(author_kind: str, body: str) -> str:
    title = "Клиент" if author_kind == "user" else "Поддержка"
    return f"<b>{title}</b>\n{html.escape(body or '')}"


def _send_topic_message(token: str, chat_id: int, topic_id: int, text: str) -> str | None:
    for chunk in _split_telegram_text(text):
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
            detail = str(exc)
            log.warning("sendMessage в тему %s failed: %s", topic_id, detail)
            return detail
    return None


def _split_telegram_text(text: str, limit: int = 4000) -> list[str]:
    """Режет длинный текст на куски под лимит Telegram, по возможности по абзацам."""
    raw = (text or "").strip()
    if not raw:
        return []
    if len(raw) <= limit:
        return [raw]
    chunks: list[str] = []
    rest = raw
    while rest:
        if len(rest) <= limit:
            chunks.append(rest)
            break
        cut = rest.rfind("\n\n", 0, limit)
        if cut < limit // 2:
            cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    return chunks


def _format_guest_history(guest_messages: list[dict]) -> str:
    """Одна сводка всей гостевой переписки для переноса в тему аккаунта."""
    if not guest_messages:
        return "<i>Сообщений в гостевом чате не было.</i>"
    blocks: list[str] = []
    for item in guest_messages:
        author = "👤 Пользователь" if item.get("author") == "user" else "💬 Поддержка"
        body = html.escape(str(item.get("body") or "").strip())
        when = html.escape(str(item.get("created_at") or "").strip())
        head = author
        if when:
            head += f" · <i>{when}</i>"
        blocks.append(f"{head}\n{body}" if body else head)
    return "\n\n".join(blocks)


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


def resolve_anchor(anchor: str) -> dict | None:
    """Запасная привязка, если в тексте сообщения бота есть user:ID или guest:ID."""
    match = _ANCHOR_RE.search(anchor or "")
    if match is None:
        return None
    kind = match.group(1)
    ref_id = int(match.group(2))
    with pool.connection() as conn:
        if kind == "user":
            row = conn.execute("SELECT 1 FROM users WHERE id = %s", (ref_id,)).fetchone()
        else:
            row = conn.execute("SELECT 1 FROM support_guests WHERE id = %s", (ref_id,)).fetchone()
    if row is None:
        return None
    return {"kind": kind, "id": ref_id}


def remember_topic(kind: str, ref_id: int, topic_id: int) -> None:
    """Запоминает тему, только если у диалога её ещё не было и id свободен."""
    if topic_id <= 0 or kind not in {"user", "guest"}:
        return
    try:
        with pool.connection() as conn:
            if kind == "user":
                conn.execute(
                    """
                    UPDATE users AS u
                    SET support_telegram_topic_id = %s
                    WHERE u.id = %s
                      AND u.support_telegram_topic_id IS NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM users o
                          WHERE o.support_telegram_topic_id = %s
                      )
                      AND NOT EXISTS (
                          SELECT 1 FROM support_guests g
                          WHERE g.telegram_topic_id = %s
                      )
                    """,
                    (topic_id, ref_id, topic_id, topic_id),
                )
                return
            conn.execute(
                """
                UPDATE support_guests AS g
                SET telegram_topic_id = %s
                WHERE g.id = %s
                  AND g.telegram_topic_id IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM support_guests o
                      WHERE o.telegram_topic_id = %s
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM users u
                      WHERE u.support_telegram_topic_id = %s
                  )
                """,
                (topic_id, ref_id, topic_id, topic_id),
            )
    except UniqueViolation:
        log.warning("тема %s уже привязана к другому диалогу", topic_id)


def after_guest_claim(
    *,
    user_id: int,
    guest_id: int,
    guest_topic_id: int | None,
    user_topic_id: int | None,
    guest_messages: list[dict],
) -> None:
    """После слияния гостя в аккаунт: переименовать тему или перенести историю и удалить гостевую."""
    threading.Thread(
        target=_after_guest_claim_safe,
        kwargs={
            "user_id": user_id,
            "guest_id": guest_id,
            "guest_topic_id": guest_topic_id,
            "user_topic_id": user_topic_id,
            "guest_messages": guest_messages,
        },
        name="support-tg-claim",
        daemon=True,
    ).start()


def _after_guest_claim_safe(
    *,
    user_id: int,
    guest_id: int,
    guest_topic_id: int | None,
    user_topic_id: int | None,
    guest_messages: list[dict],
) -> None:
    try:
        _after_guest_claim(
            user_id=user_id,
            guest_id=guest_id,
            guest_topic_id=guest_topic_id,
            user_topic_id=user_topic_id,
            guest_messages=guest_messages,
        )
    except Exception:
        log.exception("не удалось обновить Telegram после слияния гостя")


def _after_guest_claim(
    *,
    user_id: int,
    guest_id: int,
    guest_topic_id: int | None,
    user_topic_id: int | None,
    guest_messages: list[dict],
) -> None:
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
    # Итоговое имя темы — email/имя аккаунта (без «Гость #N»).
    topic_title = label[:128] or f"Клиент #{user_id}"

    # У пользователя ещё не было темы — забираем гостевую и переименовываем.
    if guest_topic_id is not None and user_topic_id is None:
        _rename_topic(token, chat_id, guest_topic_id, topic_title)
        _send_topic_message(
            token,
            chat_id,
            guest_topic_id,
            (
                f"🔄 Гостевой диалог <b>Гость #{guest_id}</b> привязан к аккаунту "
                f"<b>{html.escape(label)}</b> <code>user:{user_id}</code>."
            ),
        )
        return

    # У аккаунта уже есть тема — одной сводкой переносим историю и удаляем гостевую.
    if user_topic_id is not None and (guest_topic_id is not None or guest_messages):
        # Тема могла остаться с именем «Гость #…» после прошлого переноса — всегда обновляем.
        _rename_topic(token, chat_id, user_topic_id, topic_title)
        history = _format_guest_history(guest_messages)
        footer = (
            "✅ Перенос завершён. Гостевая тема удалена."
            if guest_topic_id is not None
            else "✅ Перенос завершён."
        )
        digest = (
            f"📦 <b>Перенесено из гостевого диалога</b> Гость #{guest_id}\n"
            f"Аккаунт: <b>{html.escape(label)}</b> <code>user:{user_id}</code>\n\n"
            f"{history}\n\n"
            f"{footer}"
        )
        _send_topic_message(token, chat_id, user_topic_id, digest)
        if guest_topic_id is not None:
            _delete_topic(token, chat_id, guest_topic_id)


def _rename_topic(token: str, chat_id: int, topic_id: int, title: str) -> None:
    name = (title or "").strip()[:128] or "Поддержка"
    try:
        _telegram_call(
            token,
            "editForumTopic",
            {
                "chat_id": str(chat_id),
                "message_thread_id": str(topic_id),
                "name": name,
            },
        )
        log.info("тема %s переименована в %r", topic_id, name)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("editForumTopic %s → %r failed: %s", topic_id, name, exc)


def _delete_topic(token: str, chat_id: int, topic_id: int) -> None:
    try:
        _telegram_call(
            token,
            "deleteForumTopic",
            {
                "chat_id": str(chat_id),
                "message_thread_id": str(topic_id),
            },
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("deleteForumTopic %s failed: %s", topic_id, exc)
