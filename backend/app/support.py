"""Чат поддержки на сайте: сообщения пользователя и ответы админки."""

from __future__ import annotations

from app.datetime_util import iso_utc
from app.db import pool

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


def list_messages(user_id: int, *, mark_seen: bool = False) -> dict:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, author_kind, body, created_at
            FROM support_messages
            WHERE user_id = %s
            ORDER BY created_at ASC, id ASC
            LIMIT %s
            """,
            (user_id, _MAX_MESSAGES),
        ).fetchall()
        unread = _unread_for_user(conn, user_id)
        if mark_seen:
            conn.execute(
                "UPDATE users SET support_seen_at = NOW() WHERE id = %s",
                (user_id,),
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
    return _message_row(row)


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
    return _message_row(row)


def unread_count(user_id: int) -> int:
    with pool.connection() as conn:
        return _unread_for_user(conn, user_id)


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


def list_threads(*, waiting_only: bool = False) -> list[dict]:
    """Список диалогов для админки: последние сообщения и «ждёт ответа»."""
    with pool.connection() as conn:
        rows = conn.execute(
            """
            WITH last AS (
                SELECT DISTINCT ON (user_id)
                    user_id, id, author_kind, body, created_at
                FROM support_messages
                ORDER BY user_id, created_at DESC, id DESC
            ),
            waiting AS (
                SELECT user_id, COUNT(*)::int AS pending
                FROM support_messages m
                WHERE author_kind = 'user'
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
            ORDER BY (COALESCE(w.pending, 0) > 0) DESC, l.created_at DESC
            """
        ).fetchall()
    threads = []
    for row in rows:
        pending = int(row["pending"] or 0)
        if waiting_only and pending <= 0:
            continue
        threads.append(
            {
                "user_id": int(row["id"]),
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
    return threads


def waiting_count() -> int:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT m.user_id)::int AS n
            FROM support_messages m
            WHERE m.author_kind = 'user'
              AND NOT EXISTS (
                  SELECT 1 FROM support_messages s
                  WHERE s.user_id = m.user_id
                    AND s.author_kind = 'staff'
                    AND s.created_at > m.created_at
              )
            """
        ).fetchone()
    return int(row["n"] or 0)
