from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.billing import BillingError, describe_key, issue_key, reissue_key, sync_user, upstream_base
from app.datetime_util import iso_utc
from app.history import HISTORY_PAGE as _HISTORY_PAGE, history_payload
from app.installer import InstallError, create_install_command
from app.usage_stats import usage_period_stats
from app.notifications import get_preferences, preferences_row, toggle_preference
from app.payments import settle_payment
from app.referrals import ReferralError, attribute_user
from app.db import pool
from app.money import bonus_tiers, min_topup_rub, min_topup_usd, rub_to_usd, topup_bonus, units_to_usd, usd_price_rub
from app.security import require_bot
from app.settings_store import consent_url, get_setting, offer_url, privacy_url, support_username
from app.telegram_link import bot_start_url, bot_username
from app.yookassa import YooKassaError, create_payment, enabled as yookassa_enabled

router = APIRouter(dependencies=[Depends(require_bot)])


class UserIn(BaseModel):
    telegram_id: int = Field(gt=0)
    username: str = Field(default="", max_length=64)
    first_name: str = Field(default="", max_length=128)


class NotificationToggleIn(BaseModel):
    key: str = Field(min_length=1, max_length=32)


class TopupIn(BaseModel):
    amount_rub: float = Field(gt=0, le=1_000_000)


class ReferralIn(BaseModel):
    token: str = Field(min_length=1, max_length=64)


class InstallIn(BaseModel):
    app: str = Field(min_length=1, max_length=32)
    os: str = Field(min_length=1, max_length=16)
    action: str = Field(default="setup", max_length=16)


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


def _public(conn, row: dict) -> dict:
    price = usd_price_rub()
    stats = usage_period_stats(conn, int(row["id"]))
    created = row.get("key_created_at")
    return {
        "id": row["id"],
        "telegram_id": row["telegram_id"],
        "balance_usd": float(row["balance_usd"]),
        "spent_today_usd": stats["spent_today_usd"],
        "spent_month_usd": stats["spent_month_usd"],
        "spent_week_usd": stats["spent_week_usd"],
        "spent_today_date": stats["spent_today_date"],
        "last_request_at": iso_utc(stats["last_request_at"]),
        "offer_accepted": row["offer_accepted_at"] is not None,
        "blocked": row["blocked_at"] is not None,
        "blocked_reason": row["blocked_reason"] or "",
        "key_prefix": row["key_prefix"] or "",
        "key_created_at": iso_utc(created),
        "has_key": bool(row["key_prefix"]),
        "offer_url": offer_url(),
        "privacy_url": privacy_url(),
        "consent_url": consent_url(),
        "support_email": (get_setting("offer_email") or get_setting("seller_email")).strip(),
        "support_username": support_username(),
        "api_base_url": upstream_base(),
        "usd_price_rub": float(price),
        "min_topup_usd": float(min_topup_usd()),
        "min_topup_rub": float(min_topup_rub()),
        "bonuses": bonus_tiers(),
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


@router.post("/users/{telegram_id}/referral")
def attach_referral(telegram_id: int, body: ReferralIn) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        user_id = int(row["id"])
    try:
        attributed = attribute_user(user_id, body.token)
    except ReferralError:
        raise HTTPException(status_code=400, detail="token")
    return {"attributed": attributed}


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
    if amount_usd < min_topup_usd():
        raise HTTPException(status_code=402, detail="min-topup")
    kopecks = int((amount_rub * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    bonus_percent, bonus_usd = topup_bonus(amount_usd)
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        if row["offer_accepted_at"] is None:
            raise HTTPException(status_code=403, detail="offer")
        created = conn.execute(
            """
            INSERT INTO topups (user_id, amount_kopecks, amount_usd, bonus_usd)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (row["id"], kopecks, amount_usd, bonus_usd),
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
        "bonus_usd": float(bonus_usd),
        "bonus_percent": float(bonus_percent),
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
    if status in ("pending", "awaiting_supplier") and topup["payment_id"]:
        try:
            result = settle_payment(str(topup["payment_id"]))
        except (YooKassaError, BillingError):
            result = status
        if result in {"credited", "already"}:
            status = "paid"
        elif result == "awaiting_supplier":
            status = "awaiting_supplier"
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
    sync_user(user_id)
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
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
        key_id = int(key["id"])
        totals = conn.execute(
            """
            SELECT COUNT(*) AS requests,
                   COALESCE(SUM(quota_units), 0) AS units
            FROM usage
            WHERE api_key_id = %s
            """,
            (key_id,),
        ).fetchone()
        items = conn.execute(
            """
            SELECT model_name, prompt_tokens, completion_tokens, quota_units, created_at
            FROM usage
            WHERE api_key_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (key_id, limit + 1, offset),
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
                "created_at": iso_utc(item["created_at"]),
            }
            for item in items[:limit]
        ],
    }


@router.post("/users/{telegram_id}/install")
def install_command(telegram_id: int, body: InstallIn) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        _require_active(row)
        user_id = int(row["id"])
    try:
        return create_install_command(user_id, body.app, body.os, body.action)
    except InstallError as exc:
        status = {"unknown": 400, "blocked": 403, "no-key": 409, "no-site": 503}.get(exc.code, 502)
        raise HTTPException(status_code=status, detail=exc.code) from exc


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


@router.get("/users/{telegram_id}/history")
def user_history(
    telegram_id: int,
    filter: str = "all",
    offset: int = 0,
    limit: int = _HISTORY_PAGE,
) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        user_id = int(row["id"])
    sync_user(user_id)
    return history_payload(user_id, filter, offset, limit)


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
