import re

from psycopg.errors import UniqueViolation

from app.db import pool

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_RESERVED_PREFIX = "paid_"


class ReferralError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def normalize_token(raw: str) -> str:
    return raw.strip()


def validate_token(token: str) -> None:
    if not token:
        raise ReferralError("empty")
    if len(token) > 64:
        raise ReferralError("long")
    if token.startswith(_RESERVED_PREFIX):
        raise ReferralError("reserved")
    if _TOKEN_RE.fullmatch(token) is None:
        raise ReferralError("format")


def create_link(token: str) -> dict:
    value = normalize_token(token)
    validate_token(value)
    try:
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO referral_links (token)
                VALUES (%s)
                RETURNING id, token, created_at
                """,
                (value,),
            ).fetchone()
    except UniqueViolation as exc:
        raise ReferralError("exists") from exc
    return _link_row(row)


def list_links() -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.token, r.created_at,
                   COUNT(DISTINCT u.id) AS visits,
                   COUNT(DISTINCT u.id) FILTER (WHERE u.offer_accepted_at IS NOT NULL) AS offers_accepted,
                   COUNT(t.id) FILTER (WHERE t.status = 'paid') AS payments,
                   COALESCE(SUM(t.amount_kopecks) FILTER (WHERE t.status = 'paid'), 0) AS topup_kopecks,
                   COALESCE(SUM(t.amount_usd) FILTER (WHERE t.status = 'paid'), 0) AS topup_usd
            FROM referral_links r
            LEFT JOIN users u ON u.referral_token = r.token
            LEFT JOIN topups t ON t.user_id = u.id
            GROUP BY r.id, r.token, r.created_at
            ORDER BY r.id DESC
            """
        ).fetchall()
    return [_stats_row(row) for row in rows]


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


def _link_row(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "token": str(row["token"]),
        "created_at": row["created_at"].isoformat(),
        "visits": 0,
        "offers_accepted": 0,
        "payments": 0,
        "topup_rub": 0.0,
        "topup_usd": 0.0,
    }


def _stats_row(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "token": str(row["token"]),
        "created_at": row["created_at"].isoformat(),
        "visits": int(row["visits"] or 0),
        "offers_accepted": int(row["offers_accepted"] or 0),
        "payments": int(row["payments"] or 0),
        "topup_rub": int(row["topup_kopecks"] or 0) / 100,
        "topup_usd": float(row["topup_usd"] or 0),
    }
