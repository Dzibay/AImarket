import logging
import re
import secrets
from decimal import Decimal, ROUND_HALF_UP

from psycopg.errors import UniqueViolation

from app.db import pool

log = logging.getLogger("app.referrals")

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
                RETURNING id, token, created_at, group_id, owner_user_id
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
        current = conn.execute(
            "SELECT owner_user_id FROM referral_links WHERE id = %s",
            (link_id,),
        ).fetchone()
        if current is None:
            raise ReferralError("link")
        if current["owner_user_id"] is not None:
            raise ReferralError("user-link")
        if group_id is not None:
            _require_group(conn, group_id)
        row = conn.execute(
            """
            UPDATE referral_links
            SET group_id = %s
            WHERE id = %s
            RETURNING id, token, created_at, group_id, owner_user_id
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
            SELECT r.id, r.token, r.created_at, r.group_id, r.owner_user_id,
                   g.name AS group_name,
                   ou.email AS owner_email,
                   ou.telegram_id AS owner_telegram_id,
                   COALESCE(c.visits, 0) AS visits,
                   COALESCE(u.offers_accepted, 0) AS offers_accepted,
                   COALESCE(u.payers, 0) AS payers,
                   COALESCE(u.payments, 0) AS payments,
                   COALESCE(u.topup_kopecks, 0) AS topup_kopecks,
                   COALESCE(u.topup_usd, 0) AS topup_usd
            FROM referral_links r
            LEFT JOIN referral_groups g ON g.id = r.group_id
            LEFT JOIN users ou ON ou.id = r.owner_user_id
            LEFT JOIN (
                SELECT token, COUNT(*)::int AS visits
                FROM referral_clicks
                GROUP BY token
            ) c ON c.token = r.token
            LEFT JOIN (
                SELECT
                    u.referral_token AS token,
                    -- Регистрация / привязка токена (на сайте это обычно вместе с офертой).
                    COUNT(DISTINCT u.id)::int AS offers_accepted,
                    COUNT(DISTINCT u.id) FILTER (
                        WHERE EXISTS (
                            SELECT 1 FROM topups tp
                            WHERE tp.user_id = u.id AND tp.status = 'paid'
                        )
                    )::int AS payers,
                    COUNT(t.id) FILTER (WHERE t.status = 'paid')::int AS payments,
                    COALESCE(SUM(t.amount_kopecks) FILTER (WHERE t.status = 'paid'), 0) AS topup_kopecks,
                    COALESCE(SUM(t.amount_usd) FILTER (WHERE t.status = 'paid'), 0) AS topup_usd
                FROM users u
                LEFT JOIN topups t ON t.user_id = u.id
                WHERE u.referral_token <> ''
                GROUP BY u.referral_token
            ) u ON u.token = r.token
            ORDER BY
                CASE WHEN r.token IN ('web') THEN 0
                     WHEN r.owner_user_id IS NOT NULL THEN 2
                     ELSE 1 END,
                r.id DESC
            """
        ).fetchall()
    # Переходов не может быть меньше регистраций: клик могли не записать
    # (старые TG-старты, атрибуция при оплате/логине без ?ref=).
    return [_stats_row(_with_visit_floor(row)) for row in rows]


def delete_link(link_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id, token, owner_user_id FROM referral_links WHERE id = %s",
            (link_id,),
        ).fetchone()
        if row is None:
            return False
        if is_system_token(str(row["token"])):
            raise ReferralError("system")
        if row["owner_user_id"] is not None:
            raise ReferralError("user-link")
        deleted = conn.execute(
            "DELETE FROM referral_links WHERE id = %s RETURNING id",
            (link_id,),
        ).fetchone()
    return deleted is not None


def ensure_user_link(user_id: int) -> dict | None:
    """Гарантирует персональную реферальную ссылку после первой оплаты.

    Без оплат токен не создаётся (None). Если ссылка уже есть — возвращает её.
    """
    with pool.connection() as conn:
        existing = conn.execute(
            """
            SELECT id, token, created_at, group_id, owner_user_id
            FROM referral_links
            WHERE owner_user_id = %s
            """,
            (user_id,),
        ).fetchone()
        if existing is not None:
            return _link_row(existing)
        paid = conn.execute(
            """
            SELECT 1 FROM topups
            WHERE user_id = %s AND status = 'paid'
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if paid is None:
            return None
        user = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
        if user is None:
            raise ReferralError("user")
        for attempt in range(8):
            token = f"u{user_id}" if attempt == 0 else f"u{user_id}_{secrets.token_hex(3)}"
            try:
                row = conn.execute(
                    """
                    INSERT INTO referral_links (token, owner_user_id)
                    VALUES (%s, %s)
                    RETURNING id, token, created_at, group_id, owner_user_id
                    """,
                    (token, user_id),
                ).fetchone()
                return _link_row(row)
            except UniqueViolation:
                raced = conn.execute(
                    """
                    SELECT id, token, created_at, group_id, owner_user_id
                    FROM referral_links WHERE owner_user_id = %s
                    """,
                    (user_id,),
                ).fetchone()
                if raced is not None:
                    return _link_row(raced)
                continue
    raise ReferralError("exists")


def user_program_stats(user_id: int) -> dict | None:
    """Статистика реферальной программы для кабинета. None — ещё нет оплаты / ссылки."""
    link = ensure_user_link(user_id)
    if link is None:
        return None
    token = link["token"]
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE((
                    SELECT COUNT(*)::int FROM referral_clicks WHERE token = %s
                ), 0) AS visits,
                COALESCE((
                    SELECT COUNT(*)::int FROM users
                    WHERE referral_token = %s
                ), 0) AS invited,
                COALESCE((
                    SELECT COUNT(*)::int FROM users u
                    WHERE u.referral_token = %s
                      AND EXISTS (
                          SELECT 1 FROM topups t
                          WHERE t.user_id = u.id AND t.status = 'paid'
                      )
                ), 0) AS payers,
                COALESCE((
                    SELECT SUM(l.amount_usd) FROM ledger l
                    WHERE l.user_id = %s
                      AND l.kind = 'credit'
                      AND l.note LIKE 'referral bonus topup:%%'
                ), 0) AS earned_usd
            """,
            (token, token, token, user_id),
        ).fetchone()
    visits = int(row["visits"] or 0)
    invited = int(row["invited"] or 0)
    if invited > visits:
        visits = invited
    return {
        "token": token,
        "visits": visits,
        "invited": invited,
        "payers": int(row["payers"] or 0),
        "earned_usd": float(Decimal(str(row["earned_usd"] or 0)).quantize(Decimal("0.0001"))),
    }


def credit_referral_bonus(*, payer_user_id: int, topup_id: int, purchase_usd: Decimal) -> Decimal:
    """Начисляет рефереру % от суммы покупки приглашённого.

    База — только purchase_usd (topups.amount_usd). Бонус к пополнению
    приглашённого (topups.bonus_usd) в расчёт не входит.
    """
    from app.money import referral_bonus_percent

    percent = referral_bonus_percent()
    if percent <= 0:
        return Decimal("0")
    paid = Decimal(str(purchase_usd or 0))
    if paid <= 0:
        return Decimal("0")

    with pool.connection() as conn:
        payer = conn.execute(
            "SELECT referral_token FROM users WHERE id = %s",
            (payer_user_id,),
        ).fetchone()
        if payer is None:
            return Decimal("0")
        token = str(payer["referral_token"] or "").strip()
        if not token:
            return Decimal("0")
        link = conn.execute(
            """
            SELECT owner_user_id FROM referral_links
            WHERE token = %s AND owner_user_id IS NOT NULL
            """,
            (token,),
        ).fetchone()
        if link is None:
            return Decimal("0")
        owner_id = int(link["owner_user_id"])
        if owner_id == payer_user_id:
            return Decimal("0")

    bonus = (paid * percent / Decimal(100)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if bonus <= 0:
        return Decimal("0")

    note = f"referral bonus topup:{topup_id}"
    with pool.connection() as conn:
        already = conn.execute(
            "SELECT 1 FROM ledger WHERE kind = 'credit' AND note = %s LIMIT 1",
            (note,),
        ).fetchone()
        if already is not None:
            return Decimal("0")
    try:
        from app.billing import BillingError, add_usd

        # Если ключ реферера заморожен — только локальный баланс, без квоты у поставщика.
        add_usd(owner_id, bonus, "credit", note, activate_frozen=False)
    except BillingError as exc:
        if exc.code == "supplier":
            log.warning(
                "реферальный бонус topup=%s owner=%s отложен: нет баланса поставщика (%.4f USD)",
                topup_id,
                owner_id,
                bonus,
            )
            return Decimal("0")
        raise
    log.info(
        "реферальный бонус %.4f USD → user=%s за topup=%s (payer=%s, %s%%)",
        bonus,
        owner_id,
        topup_id,
        payer_user_id,
        percent,
    )
    return bonus


def record_click(token: str, *, visitor_key: str = "") -> bool:
    """Фиксирует переход по ссылке. Возвращает False, если токен неизвестен."""
    value = normalize_token(token)
    if not value or value.startswith(_RESERVED_PREFIX):
        return False
    visitor = (visitor_key or "").strip()[:128]
    with pool.connection() as conn:
        link = conn.execute(
            "SELECT id FROM referral_links WHERE token = %s",
            (value,),
        ).fetchone()
        if link is None:
            return False
        # Один клик на visitor_key на токен (браузер / telegram id) — без накрутки от F5.
        if visitor:
            exists = conn.execute(
                """
                SELECT 1 FROM referral_clicks
                WHERE token = %s AND visitor_key = %s
                LIMIT 1
                """,
                (value, visitor),
            ).fetchone()
            if exists is not None:
                return True
        conn.execute(
            """
            INSERT INTO referral_clicks (token, visitor_key)
            VALUES (%s, %s)
            """,
            (value, visitor),
        )
    return True


def attribute_user(user_id: int, token: str, *, ensure_click: bool = True) -> bool:
    """Привязывает токен к пользователю. По умолчанию пишет клик user:{id}, если атрибуция новая."""
    value = normalize_token(token)
    if not value or value.startswith(_RESERVED_PREFIX):
        return False
    with pool.connection() as conn:
        link = conn.execute(
            """
            SELECT id, owner_user_id FROM referral_links WHERE token = %s
            """,
            (value,),
        ).fetchone()
        if link is None:
            return False
        # Нельзя пригласить самого себя своей же ссылкой.
        if link["owner_user_id"] is not None and int(link["owner_user_id"]) == int(user_id):
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
    if updated is None:
        return False
    # Регистрация без предварительного ?ref= / если клик потеряли — всё равно считаем переход.
    if ensure_click:
        record_click(value, visitor_key=f"user:{user_id}")
    return True


def _with_visit_floor(row: dict) -> dict:
    data = dict(row)
    visits = int(data.get("visits") or 0)
    offers = int(data.get("offers_accepted") or 0)
    if offers > visits:
        data["visits"] = offers
    return data


def _group_row(row: dict, *, tokens: int) -> dict:
    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "created_at": row["created_at"].isoformat(),
        "tokens": tokens,
    }


def _owner_label(row: dict) -> str:
    email = str(row.get("owner_email") or "").strip()
    if email:
        return email
    tg = row.get("owner_telegram_id")
    if tg:
        return f"tg:{tg}"
    owner_id = row.get("owner_user_id")
    if owner_id is not None:
        return f"user:{owner_id}"
    return ""


def _link_row(row: dict) -> dict:
    group_id = row.get("group_id")
    owner_id = row.get("owner_user_id")
    token = str(row["token"])
    return {
        "id": int(row["id"]),
        "token": token,
        "system": is_system_token(token),
        "is_user": owner_id is not None,
        "owner_user_id": int(owner_id) if owner_id is not None else None,
        "owner_label": _owner_label(row) if owner_id is not None else "",
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
    owner_id = row.get("owner_user_id")
    token = str(row["token"])
    return {
        "id": int(row["id"]),
        "token": token,
        "system": is_system_token(token),
        "is_user": owner_id is not None,
        "owner_user_id": int(owner_id) if owner_id is not None else None,
        "owner_label": _owner_label(row) if owner_id is not None else "",
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
