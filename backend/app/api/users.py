from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.billing import BillingError, describe_key, issue_key, reissue_key, sync_user, upstream_base
from app.notifications import get_preferences, preferences_row, toggle_preference
from app.payments import settle_payment
from app.db import pool
from app.money import MIN_TOPUP_USD, min_topup_rub, rub_to_usd, units_to_usd, usd_price_rub
from app.security import require_bot
from app.settings_store import consent_url, get_setting, offer_url, privacy_url, support_username
from app.telegram_link import bot_start_url, bot_username
from app.yookassa import YooKassaError, create_payment, enabled as yookassa_enabled

router = APIRouter(dependencies=[Depends(require_bot)])
_MSK = ZoneInfo("Europe/Moscow")
_WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


class UserIn(BaseModel):
    telegram_id: int = Field(gt=0)
    username: str = Field(default="", max_length=64)
    first_name: str = Field(default="", max_length=128)


class NotificationToggleIn(BaseModel):
    key: str = Field(min_length=1, max_length=32)


class TopupIn(BaseModel):
    amount_rub: float = Field(gt=0, le=1_000_000)


def raise_billing(exc: BillingError) -> None:
    status = {
        "offer": 403,
        "blocked": 403,
        "balance": 402,
        "empty": 402,
        "sales-closed": 402,
        "no-payment": 402,
        "key-exists": 409,
        "no-key": 409,
        "supplier": 409,
    }.get(exc.code, 502)
    raise HTTPException(status_code=status, detail=exc.code)


def _profile(conn, telegram_id: int) -> dict | None:
    return conn.execute(
        """
        SELECT u.id, u.telegram_id, u.username, u.first_name, u.balance_usd,
               u.offer_accepted_at, u.blocked_at, u.blocked_reason,
               u.notify_spend, u.notify_low_balance, u.notify_limit_exhausted, u.notify_topup,
               k.prefix AS key_prefix, k.created_at AS key_created_at
        FROM users u
        LEFT JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL
        WHERE u.telegram_id = %s
        """,
        (telegram_id,),
    ).fetchone()


def _spent(conn, user_id: int) -> tuple[float, float]:
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(quota_units) FILTER (
                WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'Europe/Moscow')
                    AT TIME ZONE 'Europe/Moscow'
            ), 0) AS today_units,
            COALESCE(SUM(quota_units) FILTER (
                WHERE created_at >= date_trunc('month', NOW() AT TIME ZONE 'Europe/Moscow')
                    AT TIME ZONE 'Europe/Moscow'
            ), 0) AS month_units
        FROM usage
        WHERE user_id = %s
          AND created_at >= date_trunc('month', NOW() AT TIME ZONE 'Europe/Moscow')
              AT TIME ZONE 'Europe/Moscow'
        """,
        (user_id,),
    ).fetchone()
    return float(units_to_usd(int(row["today_units"]))), float(units_to_usd(int(row["month_units"])))


def _spent_week(conn, user_id: int) -> list[dict]:
    today = datetime.now(_MSK).date()
    start = today - timedelta(days=6)
    rows = conn.execute(
        """
        SELECT (created_at AT TIME ZONE 'Europe/Moscow')::date AS day,
               COALESCE(SUM(quota_units), 0) AS units
        FROM usage
        WHERE user_id = %s
          AND (created_at AT TIME ZONE 'Europe/Moscow')::date >= %s
        GROUP BY day
        ORDER BY day
        """,
        (user_id, start),
    ).fetchall()
    by_day = {row["day"]: float(units_to_usd(int(row["units"]))) for row in rows}
    return [
        {
            "date": day.isoformat(),
            "label": _WEEKDAY_LABELS[day.weekday()],
            "usd": by_day.get(day, 0.0),
        }
        for day in (start + timedelta(days=offset) for offset in range(7))
    ]


def _public(conn, row: dict) -> dict:
    price = usd_price_rub()
    spent_today, spent_month = _spent(conn, int(row["id"]))
    created = row.get("key_created_at")
    return {
        "id": row["id"],
        "telegram_id": row["telegram_id"],
        "balance_usd": float(row["balance_usd"]),
        "spent_today_usd": spent_today,
        "spent_month_usd": spent_month,
        "spent_week_usd": _spent_week(conn, int(row["id"])),
        "offer_accepted": row["offer_accepted_at"] is not None,
        "blocked": row["blocked_at"] is not None,
        "blocked_reason": row["blocked_reason"] or "",
        "key_prefix": row["key_prefix"] or "",
        "key_created_at": created.isoformat() if created is not None else "",
        "has_key": bool(row["key_prefix"]),
        "offer_url": offer_url(),
        "privacy_url": privacy_url(),
        "consent_url": consent_url(),
        "support_email": (get_setting("offer_email") or get_setting("seller_email")).strip(),
        "support_username": support_username(),
        "api_base_url": upstream_base(),
        "usd_price_rub": float(price),
        "min_topup_usd": float(MIN_TOPUP_USD),
        "min_topup_rub": float(min_topup_rub()),
        "yookassa_enabled": yookassa_enabled() and bool(bot_start_url()),
        "notifications": preferences_row(row),
    }


def _user_or_404(conn, telegram_id: int) -> dict:
    row = _profile(conn, telegram_id)
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return row


def _require_active(row: dict) -> None:
    if row.get("blocked_at") is not None:
        raise HTTPException(status_code=403, detail="blocked")


@router.post("/users")
def upsert_user(body: UserIn) -> dict:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE
            SET username = EXCLUDED.username,
                first_name = EXCLUDED.first_name
            """,
            (body.telegram_id, body.username.strip(), body.first_name.strip()),
        )
        return _public(conn, _user_or_404(conn, body.telegram_id))


@router.get("/users/{telegram_id}")
def get_user(telegram_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        user_id = int(row["id"])
    sync_user(user_id)
    with pool.connection() as conn:
        return _public(conn, _user_or_404(conn, telegram_id))


@router.post("/users/{telegram_id}/notifications/toggle")
def toggle_notifications(telegram_id: int, body: NotificationToggleIn) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        user_id = int(row["id"])
    try:
        prefs = toggle_preference(user_id, body.key.strip().lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="unknown-key")
    return {"notifications": prefs}


@router.post("/users/{telegram_id}/offer")
def accept_offer(telegram_id: int) -> dict:
    if not offer_url():
        raise HTTPException(status_code=409, detail="no-offer-url")
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        conn.execute(
            """
            UPDATE users
            SET offer_accepted_at = COALESCE(offer_accepted_at, NOW())
            WHERE id = %s
            """,
            (row["id"],),
        )
        return _public(conn, _user_or_404(conn, telegram_id))


@router.post("/users/{telegram_id}/topups")
def create_topup(telegram_id: int, body: TopupIn) -> dict:
    price = usd_price_rub()
    if price <= 0:
        raise HTTPException(status_code=402, detail="sales-closed")
    if not yookassa_enabled():
        raise HTTPException(status_code=402, detail="no-yookassa")
    if not bot_username():
        raise HTTPException(status_code=402, detail="no-bot")
    amount_rub = Decimal(str(body.amount_rub)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    min_rub = min_topup_rub()
    if min_rub <= 0 or amount_rub < min_rub:
        raise HTTPException(status_code=402, detail="min-topup")
    amount_usd = rub_to_usd(amount_rub)
    if amount_usd < MIN_TOPUP_USD:
        raise HTTPException(status_code=402, detail="min-topup")
    kopecks = int((amount_rub * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        if row["offer_accepted_at"] is None:
            raise HTTPException(status_code=403, detail="offer")
        created = conn.execute(
            """
            INSERT INTO topups (user_id, amount_kopecks, amount_usd)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (row["id"], kopecks, amount_usd),
        ).fetchone()
    topup_id = int(created["id"])
    return_url = bot_start_url(f"paid_{topup_id}")
    if not return_url:
        with pool.connection() as conn:
            conn.execute("UPDATE topups SET status = 'failed', decided_at = NOW() WHERE id = %s", (topup_id,))
        raise HTTPException(status_code=402, detail="no-bot")
    try:
        payment = create_payment(topup_id, amount_rub, return_url)
    except YooKassaError as exc:
        with pool.connection() as conn:
            conn.execute("UPDATE topups SET status = 'failed', decided_at = NOW() WHERE id = %s", (topup_id,))
        raise HTTPException(status_code=502, detail="yookassa") from exc
    with pool.connection() as conn:
        conn.execute("UPDATE topups SET payment_id = %s WHERE id = %s", (payment["id"], topup_id))
    return {
        "id": topup_id,
        "amount_rub": float(amount_rub),
        "amount_usd": float(amount_usd),
        "pay_url": payment["url"],
    }


@router.post("/users/{telegram_id}/topups/{topup_id}/check")
def check_topup(telegram_id: int, topup_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        topup = conn.execute(
            """
            SELECT payment_id, status, amount_usd
            FROM topups
            WHERE id = %s AND user_id = %s
            """,
            (topup_id, row["id"]),
        ).fetchone()
    if topup is None:
        raise HTTPException(status_code=404, detail="topup")
    status = str(topup["status"])
    if status == "pending" and topup["payment_id"]:
        try:
            result = settle_payment(str(topup["payment_id"]))
        except (YooKassaError, BillingError):
            result = "pending"
        if result in {"credited", "already"}:
            status = "paid"
    with pool.connection() as conn:
        fresh = _user_or_404(conn, telegram_id)
    return {
        "status": status,
        "balance_usd": float(fresh["balance_usd"]),
        "amount_usd": float(topup["amount_usd"]),
    }


@router.get("/users/{telegram_id}/key")
def read_key(telegram_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        user_id = int(row["id"])
    sync_user(user_id)
    try:
        return describe_key(user_id)
    except BillingError as exc:
        raise_billing(exc)


def _mask_key_label(secret: str, prefix: str = "") -> str:
    value = secret or prefix
    if len(value) <= 12:
        return value or "API-ключ"
    return f"{value[:8]}...{value[-4:]}"


@router.get("/users/{telegram_id}/key/history")
def key_history(
    telegram_id: int,
    offset: int = 0,
    limit: int = _HISTORY_PAGE,
) -> dict:
    offset = max(0, offset)
    limit = min(max(1, limit), 30)
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        user_id = int(row["id"])
        key = conn.execute(
            """
            SELECT id, name, prefix, secret
            FROM api_keys
            WHERE user_id = %s AND revoked_at IS NULL AND upstream_id IS NOT NULL
            """,
            (user_id,),
        ).fetchone()
        if key is None:
            raise HTTPException(status_code=404, detail="no-key")
        totals = conn.execute(
            """
            SELECT COUNT(*) AS requests,
                   COALESCE(SUM(quota_units), 0) AS units
            FROM usage
            WHERE api_key_id = %s
            """,
            (key["id"],),
        ).fetchone()
        items = conn.execute(
            """
            SELECT model_name, prompt_tokens, completion_tokens, quota_units, created_at
            FROM usage
            WHERE api_key_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (key["id"], limit + 1, offset),
        ).fetchall()
    has_more = len(items) > limit
    key_label = _mask_key_label(str(key["secret"] or ""), str(key["prefix"] or key["name"] or ""))
    return {
        "key_name": key_label,
        "total_requests": int(totals["requests"] or 0),
        "total_usd": float(units_to_usd(int(totals["units"] or 0))),
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "items": [
            {
                "model": str(item["model_name"] or "—"),
                "prompt_tokens": int(item["prompt_tokens"] or 0),
                "completion_tokens": int(item["completion_tokens"] or 0),
                "amount_usd": float(units_to_usd(int(item["quota_units"] or 0))),
                "created_at": item["created_at"].isoformat() if item["created_at"] is not None else "",
            }
            for item in items[:limit]
        ],
    }


@router.post("/users/{telegram_id}/keys")
def create_key(telegram_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        user_id = int(row["id"])
    try:
        return issue_key(user_id, telegram_id)
    except BillingError as exc:
        raise_billing(exc)


_HISTORY_KINDS = {
    "topup": "Пополнение",
    "credit": "Начисление",
    "spend": "Расход",
    "adjust": "Сверка",
}
_HISTORY_PAGE = 5


def _history_filter(raw: str) -> str:
    value = (raw or "all").strip().lower()
    if value in {"income", "in", "topup", "topups"}:
        return "income"
    if value in {"spend", "out", "spends"}:
        return "spend"
    return "all"


def _history_item(row: dict) -> dict:
    entry_type = str(row["entry_type"])
    kind = str(row["kind"])
    if entry_type == "income":
        return {
            "entry_type": "income",
            "kind": kind,
            "label": _HISTORY_KINDS.get(kind, kind),
            "note": row["note"] or "",
            "amount_usd": float(row["amount_usd"]),
            "amount_rub": float(int(row["amount_kopecks"] or 0)) / 100,
            "created_at": row["created_at"].isoformat() if row["created_at"] is not None else "",
        }
    return {
        "entry_type": "spend",
        "kind": "spend",
        "label": "Расход",
        "model": str(row["model_name"] or "—"),
        "prompt_tokens": int(row["prompt_tokens"] or 0),
        "completion_tokens": int(row["completion_tokens"] or 0),
        "amount_usd": float(units_to_usd(int(row["quota_units"] or 0))),
        "created_at": row["created_at"].isoformat() if row["created_at"] is not None else "",
    }


@router.get("/users/{telegram_id}/history")
def user_history(
    telegram_id: int,
    filter: str = "all",
    offset: int = 0,
    limit: int = _HISTORY_PAGE,
) -> dict:
    kind = _history_filter(filter)
    offset = max(0, offset)
    limit = min(max(1, limit), 30)
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        user_id = int(row["id"])
        parts: list[str] = []
        params: list[object] = []
        if kind in {"all", "income"}:
            parts.append(
                """
                SELECT 'income' AS entry_type, kind, note, amount_usd, amount_kopecks,
                       NULL::text AS model_name, NULL::int AS prompt_tokens,
                       NULL::int AS completion_tokens, NULL::bigint AS quota_units, created_at
                FROM ledger
                WHERE user_id = %s AND kind IN ('topup', 'credit')
                """
            )
            params.append(user_id)
        if kind in {"all", "spend"}:
            parts.append(
                """
                SELECT 'spend' AS entry_type, 'spend' AS kind, '' AS note,
                       0::numeric AS amount_usd, 0 AS amount_kopecks,
                       model_name, prompt_tokens, completion_tokens, quota_units, created_at
                FROM usage
                WHERE user_id = %s
                """
            )
            params.append(user_id)
        if not parts:
            return {"items": [], "offset": offset, "limit": limit, "has_more": False, "filter": kind}
        query = f"""
            SELECT * FROM (
                {" UNION ALL ".join(parts)}
            ) history
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit + 1, offset])
        rows = conn.execute(query, tuple(params)).fetchall()
        has_any = True
        if offset == 0 and not rows:
            income = conn.execute(
                """
                SELECT 1 FROM ledger
                WHERE user_id = %s AND kind IN ('topup', 'credit')
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            usage = conn.execute(
                "SELECT 1 FROM usage WHERE user_id = %s LIMIT 1",
                (user_id,),
            ).fetchone()
            has_any = income is not None or usage is not None
    has_more = len(rows) > limit
    items = [_history_item(row) for row in rows[:limit]]
    return {
        "items": items,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "filter": kind,
        "has_any": has_any,
    }


@router.post("/users/{telegram_id}/keys/reissue")
def rotate_key(telegram_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        user_id = int(row["id"])
    try:
        return reissue_key(user_id, telegram_id)
    except BillingError as exc:
        raise_billing(exc)
