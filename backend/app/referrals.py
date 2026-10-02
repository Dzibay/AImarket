import re

from psycopg.errors import UniqueViolation

from app.db import pool

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_RESERVED_PREFIX = "paid_"
# Системные токены: создаются при старте, нельзя создать/удалить вручную.
_SYSTEM_TOKENS = frozenset({"web"})
_GROUP_NAME_RE = re.compile(r"^[\w\s\-А-Яа-яЁё]{1,64}$", re.UNICODE)


class ReferralError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def is_system_token(token: str) -> bool:
    return normalize_token(token) in _SYSTEM_TOKENS


def ensure_system_links() -> None:
    """Гарантирует наличие токенов (например web для кнопки с сайта)."""
    with pool.connection() as conn:
        for token in sorted(_SYSTEM_TOKENS):
            conn.execute(
                """
                INSERT INTO referral_links (token)
                VALUES (%s)
                ON CONFLICT (token) DO NOTHING
                """,
                (token,),
            )


def normalize_token(raw: str) -> str:
    return raw.strip()


def normalize_group_name(raw: str) -> str:
    return " ".join(raw.strip().split())


def validate_token(token: str) -> None:
    if not token:
        raise ReferralError("empty")
    if len(token) > 64:
        raise ReferralError("long")
    if token.startswith(_RESERVED_PREFIX) or token in _SYSTEM_TOKENS:
        raise ReferralError("reserved")
    if _TOKEN_RE.fullmatch(token) is None:
        raise ReferralError("format")


def validate_group_name(name: str) -> None:
    if not name:
        raise ReferralError("empty")
    if len(name) > 64:
        raise ReferralError("long")
    if _GROUP_NAME_RE.fullmatch(name) is None:
        raise ReferralError("format")


def _require_group(conn, group_id: int) -> None:
    row = conn.execute("SELECT id FROM referral_groups WHERE id = %s", (group_id,)).fetchone()
    if row is None:
        raise ReferralError("group")


def create_group(name: str) -> dict:
    value = normalize_group_name(name)
    validate_group_name(value)
    try:
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO referral_groups (name)
                VALUES (%s)
                RETURNING id, name, created_at
                """,
                (value,),
            ).fetchone()
    except UniqueViolation as exc:
        raise ReferralError("exists") from exc
    return _group_row(row, tokens=0)


def list_groups() -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT g.id, g.name, g.created_at, COUNT(r.id) AS tokens
            FROM referral_groups g
            LEFT JOIN referral_links r ON r.group_id = g.id
            GROUP BY g.id, g.name, g.created_at
            ORDER BY g.name
            """
        ).fetchall()
    return [_group_row(row, tokens=int(row["tokens"] or 0)) for row in rows]


def delete_group(group_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            "DELETE FROM referral_groups WHERE id = %s RETURNING id",
            (group_id,),
        ).fetchone()
    return row is not None


def create_link(token: str, group_id: int | None = None) -> dict:
    value = normalize_token(token)
    validate_token(value)
    with pool.connection() as conn:
        if group_id is not None:
            _require_group(conn, group_id)
        try:
            row = conn.execute(
                """
                INSERT INTO referral_links (token, group_id)
                VALUES (%s, %s)
                RETURNING id, token, created_at, group_id
                """,
                (value, group_id),
            ).fetchone()
        except UniqueViolation as exc:
            raise ReferralError("exists") from exc
        group_name = ""
        if row["group_id"] is not None:
            group = conn.execute(
                "SELECT name FROM referral_groups WHERE id = %s",
                (int(row["group_id"]),),
            ).fetchone()
            group_name = str(group["name"]) if group else ""
    result = _link_row(row)
    result["group_name"] = group_name
    return result


def set_link_group(link_id: int, group_id: int | None) -> dict:
    with pool.connection() as conn:
        if group_id is not None:
            _require_group(conn, group_id)
        row = conn.execute(
            """
            UPDATE referral_links
            SET group_id = %s
            WHERE id = %s
            RETURNING id, token, created_at, group_id
            """,
            (group_id, link_id),
        ).fetchone()
        if row is None:
            raise ReferralError("link")
        group_name = ""
        if row["group_id"] is not None:
            group = conn.execute(
                "SELECT name FROM referral_groups WHERE id = %s",
                (int(row["group_id"]),),
            ).fetchone()
            group_name = str(group["name"]) if group else ""
    result = _link_row(row)
    result["group_name"] = group_name
    return result


def list_links() -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.token, r.created_at, r.group_id, g.name AS group_name,
                   COUNT(DISTINCT u.id) AS visits,
                   COUNT(DISTINCT u.id) FILTER (WHERE u.offer_accepted_at IS NOT NULL) AS offers_accepted,
                   COUNT(DISTINCT u.id) FILTER (WHERE t.status = 'paid') AS payers,
                   COUNT(t.id) FILTER (WHERE t.status = 'paid') AS payments,
                   COALESCE(SUM(t.amount_kopecks) FILTER (WHERE t.status = 'paid'), 0) AS topup_kopecks,
                   COALESCE(SUM(t.amount_usd) FILTER (WHERE t.status = 'paid'), 0) AS topup_usd
            FROM referral_links r
            LEFT JOIN referral_groups g ON g.id = r.group_id
            LEFT JOIN users u ON u.referral_token = r.token
            LEFT JOIN topups t ON t.user_id = u.id
            GROUP BY r.id, r.token, r.created_at, r.group_id, g.name
            ORDER BY CASE WHEN r.token IN ('web') THEN 0 ELSE 1 END, r.id DESC
            """
        ).fetchall()
    return [_stats_row(row) for row in rows]


def delete_link(link_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id, token FROM referral_links WHERE id = %s",
            (link_id,),
        ).fetchone()
        if row is None:
            return False
        if is_system_token(str(row["token"])):
            raise ReferralError("system")
        deleted = conn.execute(
            "DELETE FROM referral_links WHERE id = %s RETURNING id",
            (link_id,),
        ).fetchone()
    return deleted is not None


def attribute_user(user_id: int, token: str) -> bool:
    value = normalize_token(token)
    if not value or value.startswith(_RESERVED_PREFIX):
        return False
    with pool.connection() as conn:
        link = conn.execute(
            "SELECT id FROM referral_links WHERE token = %s",
            (value,),
        ).fetchone()
        if link is None:
            return False
        updated = conn.execute(
            """
            UPDATE users
            SET referral_token = %s
            WHERE id = %s AND (referral_token IS NULL OR referral_token = '')
            RETURNING id
            """,
            (value, user_id),
        ).fetchone()
    return updated is not None


def _group_row(row: dict, *, tokens: int) -> dict:
    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "created_at": row["created_at"].isoformat(),
        "tokens": tokens,
    }


def _link_row(row: dict) -> dict:
    group_id = row.get("group_id")
    token = str(row["token"])
    return {
        "id": int(row["id"]),
        "token": token,
        "system": is_system_token(token),
        "created_at": row["created_at"].isoformat(),
        "group_id": int(group_id) if group_id is not None else None,
        "group_name": "",
        "visits": 0,
        "offers_accepted": 0,
        "payers": 0,
        "payments": 0,
        "payment_conversion": 0.0,
        "topup_rub": 0.0,
        "topup_usd": 0.0,
    }


def _stats_row(row: dict) -> dict:
    visits = int(row["visits"] or 0)
    payers = int(row["payers"] or 0)
    conversion = round(payers / visits * 100, 1) if visits > 0 else 0.0
    group_id = row.get("group_id")
    token = str(row["token"])
    return {
        "id": int(row["id"]),
        "token": token,
        "system": is_system_token(token),
        "created_at": row["created_at"].isoformat(),
        "group_id": int(group_id) if group_id is not None else None,
        "group_name": str(row.get("group_name") or ""),
        "visits": visits,
        "offers_accepted": int(row["offers_accepted"] or 0),
        "payers": payers,
        "payments": int(row["payments"] or 0),
        "payment_conversion": conversion,
        "topup_rub": int(row["topup_kopecks"] or 0) / 100,
        "topup_usd": float(row["topup_usd"] or 0),
    }
