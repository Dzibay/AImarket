"""Чат поддержки на сайте: сообщения пользователя/гостя и ответы админки."""

from __future__ import annotations

import logging
import secrets

from app.datetime_util import iso_utc
from app.db import pool
from app.support_telegram import (
    after_guest_claim,
    forward_staff_message,
    forward_user_message,
    notify_telegram_message,
)
from app.web_auth import key_hash

log = logging.getLogger("app.support")

_MAX_BODY = 4000
_MAX_MESSAGES = 200


def normalize_body(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ValueError("message")
    if len(text) > _MAX_BODY:
        raise ValueError("long")
    return text


def _message_row(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "author": row["author_kind"],
        "body": row["body"],
        "created_at": iso_utc(row["created_at"]),
    }


def ensure_guest_token(raw_token: str = "") -> str:
    """Возвращает действующий гостевой токен: существующий или новый."""
    token = (raw_token or "").strip()
    if token:
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT id FROM support_guests WHERE token_hash = %s",
                (key_hash(token),),
            ).fetchone()
        if row is not None:
            return token
    token = secrets.token_urlsafe(32)
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO support_guests (token_hash) VALUES (%s)",
            (key_hash(token),),
        )
    return token


def _guest_id(conn, token: str) -> int:
    row = conn.execute(
        "SELECT id FROM support_guests WHERE token_hash = %s",
        (key_hash(token.strip()),),
    ).fetchone()
    if row is None:
        raise LookupError("token")
    return int(row["id"])


def claim_guest_messages(user_id: int, raw_token: str) -> int:
    """Переносит гостевой диалог к авторизованному пользователю. Возвращает число сообщений."""
    token = (raw_token or "").strip()
    if not token:
        return 0
    guest_topic_id: int | None = None
    user_topic_id: int | None = None
    guest_id = 0
    guest_messages: list[dict] = []
    with pool.connection() as conn:
        guest = conn.execute(
            "SELECT id, seen_at, telegram_topic_id FROM support_guests WHERE token_hash = %s",
            (key_hash(token),),
        ).fetchone()
        if guest is None:
            return 0
        guest_id = int(guest["id"])
        guest_topic_id = int(guest["telegram_topic_id"]) if guest["telegram_topic_id"] is not None else None
        user = conn.execute(
            "SELECT id, support_seen_at, support_telegram_topic_id FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
        if user is None:
            raise LookupError("user")
        user_topic_id = (
            int(user["support_telegram_topic_id"])
            if user["support_telegram_topic_id"] is not None
            else None
        )

        guest_seen = guest["seen_at"]
        user_seen = user["support_seen_at"]
        if guest_seen is not None:
            if user_seen is None:
                merged_seen = guest_seen
            else:
                merged_seen = min(user_seen, guest_seen)
            conn.execute(
                "UPDATE users SET support_seen_at = %s WHERE id = %s",
                (merged_seen, user_id),
            )

        # Снимок гостевой переписки до переноса (для Telegram-темы аккаунта).
        rows = conn.execute(
            """
            SELECT author_kind, body, created_at
            FROM support_messages
            WHERE guest_id = %s
            ORDER BY created_at ASC, id ASC
            LIMIT %s
            """,
            (guest_id, _MAX_MESSAGES),
        ).fetchall()
        guest_messages = [
            {
                "author": row["author_kind"],
                "body": row["body"],
                "created_at": iso_utc(row["created_at"]),
            }
            for row in rows
        ]

        # Если у пользователя ещё нет темы — забираем гостевую.
        if guest_topic_id is not None and user_topic_id is None:
            conn.execute(
                "UPDATE users SET support_telegram_topic_id = %s WHERE id = %s",
                (guest_topic_id, user_id),
            )
            conn.execute(
                "UPDATE support_guests SET telegram_topic_id = NULL WHERE id = %s",
                (guest_id,),
            )

        moved = conn.execute(
            """
            UPDATE support_messages
            SET user_id = %s, guest_id = NULL
            WHERE guest_id = %s
            """,
            (user_id, guest_id),
        )
        count = int(moved.rowcount or 0)
        # Перед удалением гостя отвязываем тему, если она осталась (случай «у аккаунта уже есть тема»).
        if guest_topic_id is not None and user_topic_id is not None:
            conn.execute(
                "UPDATE support_guests SET telegram_topic_id = NULL WHERE id = %s",
                (guest_id,),
            )
        conn.execute("DELETE FROM support_guests WHERE id = %s", (guest_id,))
        conn.execute(
            """
            UPDATE users
            SET support_telegram_synced_id = (
                SELECT MAX(id) FROM support_messages WHERE user_id = %s
            )
            WHERE id = %s
              AND support_telegram_topic_id IS NOT NULL
            """,
            (user_id, user_id),
        )

    # guest_topic_id / user_topic_id — значения до слияния.
    after_guest_claim(
        user_id=user_id,
        guest_id=guest_id,
        guest_topic_id=guest_topic_id,
        user_topic_id=user_topic_id,
        guest_messages=guest_messages,
    )
    return count


def _recent_messages(conn, column: str, ref_id: int) -> list:
    if column not in {"user_id", "guest_id"}:
        raise ValueError(column)
    return conn.execute(
        f"""
        SELECT id, author_kind, body, created_at
        FROM (
            SELECT id, author_kind, body, created_at
            FROM support_messages
            WHERE {column} = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
        ) recent
        ORDER BY created_at ASC, id ASC
        """,
        (ref_id, _MAX_MESSAGES),
    ).fetchall()


def list_messages(user_id: int, *, mark_seen: bool = False) -> dict:
    with pool.connection() as conn:
        rows = _recent_messages(conn, "user_id", user_id)
        unread = _unread_for_user(conn, user_id)
        prefs = conn.execute(
            """
            SELECT email, notify_support_email
            FROM users WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
        if mark_seen:
            conn.execute(
                "UPDATE users SET support_seen_at = NOW() WHERE id = %s",
                (user_id,),
            )
            unread = 0
    from app.mailer import enabled as mail_enabled

    has_email = bool(prefs and (prefs["email"] or "").strip())
    return {
        "messages": [_message_row(row) for row in rows],
        "unread": unread,
        "email_notify": {
            "available": has_email and mail_enabled(),
            "enabled": bool(prefs["notify_support_email"]) if prefs is not None else True,
        },
    }


def set_support_email_notify(user_id: int, enabled: bool) -> dict:
    from app.mailer import enabled as mail_enabled

    with pool.connection() as conn:
        row = conn.execute(
            """
            UPDATE users
            SET notify_support_email = %s
            WHERE id = %s
            RETURNING email, notify_support_email
            """,
            (bool(enabled), user_id),
        ).fetchone()
    if row is None:
        raise LookupError("user")
    has_email = bool((row["email"] or "").strip())
    return {
        "email_notify": {
            "available": has_email and mail_enabled(),
            "enabled": bool(row["notify_support_email"]),
        }
    }


def _notify_support_email(user_id: int, body: str) -> None:
    try:
        from app.mailer import maybe_send_support_reply_email

        maybe_send_support_reply_email(user_id, body)
    except Exception:
        log.exception("не удалось отправить письмо о ответе поддержки user=%s", user_id)


def list_guest_messages(token: str, *, mark_seen: bool = False) -> dict:
    with pool.connection() as conn:
        guest_id = _guest_id(conn, token)
        rows = _recent_messages(conn, "guest_id", guest_id)
        unread = _unread_for_guest(conn, guest_id)
        if mark_seen:
            conn.execute(
                "UPDATE support_guests SET seen_at = NOW() WHERE id = %s",
                (guest_id,),
            )
            unread = 0
    return {"messages": [_message_row(row) for row in rows], "unread": unread}


def post_user_message(user_id: int, body: str) -> dict:
    text = normalize_body(body)
    with pool.connection() as conn:
        blocked = conn.execute(
            "SELECT blocked_at FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
        if blocked is None:
            raise LookupError("user")
        if blocked["blocked_at"] is not None:
            raise PermissionError("blocked")
        row = conn.execute(
            """
            INSERT INTO support_messages (user_id, author_kind, body)
            VALUES (%s, 'user', %s)
            RETURNING id, author_kind, body, created_at
            """,
            (user_id, text),
        ).fetchone()
        conn.execute(
            "UPDATE users SET support_seen_at = NOW() WHERE id = %s",
            (user_id,),
        )
    message = _message_row(row)
    forward_user_message(user_id=user_id, body=text, message_id=message["id"])
    return message


def post_guest_message(token: str, body: str) -> dict:
    text = normalize_body(body)
    with pool.connection() as conn:
        guest_id = _guest_id(conn, token)
        row = conn.execute(
            """
            INSERT INTO support_messages (guest_id, author_kind, body)
            VALUES (%s, 'user', %s)
            RETURNING id, author_kind, body, created_at
            """,
            (guest_id, text),
        ).fetchone()
        conn.execute(
            "UPDATE support_guests SET seen_at = NOW() WHERE id = %s",
            (guest_id,),
        )
    message = _message_row(row)
    forward_user_message(guest_id=guest_id, body=text, message_id=message["id"])
    return message


def post_staff_message(user_id: int, body: str) -> dict:
    text = normalize_body(body)
    with pool.connection() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE id = %s", (user_id,)).fetchone()
        if exists is None:
            raise LookupError("user")
        row = conn.execute(
            """
            INSERT INTO support_messages (user_id, author_kind, body)
            VALUES (%s, 'staff', %s)
            RETURNING id, author_kind, body, created_at
            """,
            (user_id, text),
        ).fetchone()
    message = _message_row(row)
    forward_staff_message(user_id=user_id, body=text, message_id=message["id"])
    _notify_support_email(user_id, text)
    return message


def post_staff_guest_message(guest_id: int, body: str) -> dict:
    text = normalize_body(body)
    with pool.connection() as conn:
        exists = conn.execute("SELECT 1 FROM support_guests WHERE id = %s", (guest_id,)).fetchone()
        if exists is None:
            raise LookupError("guest")
        row = conn.execute(
            """
            INSERT INTO support_messages (guest_id, author_kind, body)
            VALUES (%s, 'staff', %s)
            RETURNING id, author_kind, body, created_at
            """,
            (guest_id, text),
        ).fetchone()
    message = _message_row(row)
    forward_staff_message(guest_id=guest_id, body=text, message_id=message["id"])
    return message

# Keep a silent path for Telegram→site replies (без эха обратно в группу).
def post_staff_message_from_telegram(user_id: int, body: str) -> dict:
    text = normalize_body(body)
    with pool.connection() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE id = %s", (user_id,)).fetchone()
        if exists is None:
            raise LookupError("user")
        row = conn.execute(
            """
            INSERT INTO support_messages (user_id, author_kind, source, body)
            VALUES (%s, 'staff', 'telegram', %s)
            RETURNING id, author_kind, body, created_at
            """,
            (user_id, text),
        ).fetchone()
    message = _message_row(row)
    notify_telegram_message(user_id=user_id, message_id=message["id"])
    _notify_support_email(user_id, text)
    return message


def post_staff_guest_message_from_telegram(guest_id: int, body: str) -> dict:
    text = normalize_body(body)
    with pool.connection() as conn:
        exists = conn.execute("SELECT 1 FROM support_guests WHERE id = %s", (guest_id,)).fetchone()
        if exists is None:
            raise LookupError("guest")
        row = conn.execute(
            """
            INSERT INTO support_messages (guest_id, author_kind, source, body)
            VALUES (%s, 'staff', 'telegram', %s)
            RETURNING id, author_kind, body, created_at
            """,
            (guest_id, text),
        ).fetchone()
    message = _message_row(row)
    notify_telegram_message(guest_id=guest_id, message_id=message["id"])
    return message


def unread_count(user_id: int) -> int:
    with pool.connection() as conn:
        return _unread_for_user(conn, user_id)


def guest_unread_count(token: str) -> int:
    with pool.connection() as conn:
        guest_id = _guest_id(conn, token)
        return _unread_for_guest(conn, guest_id)


def _unread_for_user(conn, user_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*)::int AS n
        FROM support_messages m
        JOIN users u ON u.id = m.user_id
        WHERE m.user_id = %s
          AND m.author_kind = 'staff'
          AND (u.support_seen_at IS NULL OR m.created_at > u.support_seen_at)
        """,
        (user_id,),
    ).fetchone()
    return int(row["n"] or 0)


def _unread_for_guest(conn, guest_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*)::int AS n
        FROM support_messages m
        JOIN support_guests g ON g.id = m.guest_id
        WHERE m.guest_id = %s
          AND m.author_kind = 'staff'
          AND (g.seen_at IS NULL OR m.created_at > g.seen_at)
        """,
        (guest_id,),
    ).fetchone()
    return int(row["n"] or 0)


def list_guest_messages_by_id(guest_id: int) -> dict:
    with pool.connection() as conn:
        exists = conn.execute("SELECT 1 FROM support_guests WHERE id = %s", (guest_id,)).fetchone()
        if exists is None:
            raise LookupError("guest")
        rows = _recent_messages(conn, "guest_id", guest_id)
    return {"messages": [_message_row(row) for row in rows], "unread": 0}


def list_threads(*, waiting_only: bool = False) -> list[dict]:
    """Список диалогов для админки: пользователи и гости."""
    with pool.connection() as conn:
        user_rows = conn.execute(
            """
            WITH last AS (
                SELECT DISTINCT ON (user_id)
                    user_id, id, author_kind, body, created_at
                FROM support_messages
                WHERE user_id IS NOT NULL
                ORDER BY user_id, created_at DESC, id DESC
            ),
            waiting AS (
                SELECT user_id, COUNT(*)::int AS pending
                FROM support_messages m
                WHERE user_id IS NOT NULL
                  AND author_kind = 'user'
                  AND NOT EXISTS (
                      SELECT 1 FROM support_messages s
                      WHERE s.user_id = m.user_id
                        AND s.author_kind = 'staff'
                        AND s.created_at > m.created_at
                  )
                GROUP BY user_id
            )
            SELECT u.id, u.email, u.username, u.first_name, u.telegram_id,
                   l.author_kind AS last_author, l.body AS last_body,
                   l.created_at AS last_at,
                   COALESCE(w.pending, 0) AS pending
            FROM last l
            JOIN users u ON u.id = l.user_id
            LEFT JOIN waiting w ON w.user_id = u.id
            """
        ).fetchall()
        guest_rows = conn.execute(
            """
            WITH last AS (
                SELECT DISTINCT ON (guest_id)
                    guest_id, id, author_kind, body, created_at
                FROM support_messages
                WHERE guest_id IS NOT NULL
                ORDER BY guest_id, created_at DESC, id DESC
            ),
            waiting AS (
                SELECT guest_id, COUNT(*)::int AS pending
                FROM support_messages m
                WHERE guest_id IS NOT NULL
                  AND author_kind = 'user'
                  AND NOT EXISTS (
                      SELECT 1 FROM support_messages s
                      WHERE s.guest_id = m.guest_id
                        AND s.author_kind = 'staff'
                        AND s.created_at > m.created_at
                  )
                GROUP BY guest_id
            )
            SELECT g.id, g.created_at AS guest_created,
                   l.author_kind AS last_author, l.body AS last_body,
                   l.created_at AS last_at,
                   COALESCE(w.pending, 0) AS pending
            FROM last l
            JOIN support_guests g ON g.id = l.guest_id
            LEFT JOIN waiting w ON w.guest_id = g.id
            """
        ).fetchall()

    threads: list[dict] = []
    for row in user_rows:
        pending = int(row["pending"] or 0)
        if waiting_only and pending <= 0:
            continue
        threads.append(
            {
                "kind": "user",
                "id": int(row["id"]),
                "thread_key": f"user:{int(row['id'])}",
                "email": row["email"] or "",
                "username": row["username"] or "",
                "first_name": row["first_name"] or "",
                "telegram_id": int(row["telegram_id"]) if row["telegram_id"] else None,
                "last_author": row["last_author"],
                "last_body": row["last_body"],
                "last_at": iso_utc(row["last_at"]),
                "pending": pending,
                "waiting": pending > 0,
            }
        )
    for row in guest_rows:
        pending = int(row["pending"] or 0)
        if waiting_only and pending <= 0:
            continue
        guest_id = int(row["id"])
        threads.append(
            {
                "kind": "guest",
                "id": guest_id,
                "thread_key": f"guest:{guest_id}",
                "email": "",
                "username": "",
                "first_name": f"Гость #{guest_id}",
                "telegram_id": None,
                "last_author": row["last_author"],
                "last_body": row["last_body"],
                "last_at": iso_utc(row["last_at"]),
                "pending": pending,
                "waiting": pending > 0,
            }
        )
    threads.sort(key=lambda item: (item["waiting"], item["last_at"] or ""), reverse=True)
    return threads


def waiting_count() -> int:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*)::int AS n FROM (
                SELECT DISTINCT user_id AS tid
                FROM support_messages m
                WHERE user_id IS NOT NULL
                  AND author_kind = 'user'
                  AND NOT EXISTS (
                      SELECT 1 FROM support_messages s
                      WHERE s.user_id = m.user_id
                        AND s.author_kind = 'staff'
                        AND s.created_at > m.created_at
                  )
                UNION
                SELECT DISTINCT guest_id AS tid
                FROM support_messages m
                WHERE guest_id IS NOT NULL
                  AND author_kind = 'user'
                  AND NOT EXISTS (
                      SELECT 1 FROM support_messages s
                      WHERE s.guest_id = m.guest_id
                        AND s.author_kind = 'staff'
                        AND s.created_at > m.created_at
                  )
            ) t
            """
        ).fetchone()
    return int(row["n"] or 0)
