from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.billing import BillingError, issue_key, reissue_key, sync_user
from app.payments import settle_payment
from app.db import pool
from app.money import rub_to_usd, usd_price_rub
from app.security import require_bot
from app.settings_store import offer_url
from app.telegram_link import bot_start_url, bot_username
from app.yookassa import YooKassaError, create_payment, enabled as yookassa_enabled

router = APIRouter(dependencies=[Depends(require_bot)])


class UserIn(BaseModel):
    telegram_id: int = Field(gt=0)
    username: str = Field(default="", max_length=64)
    first_name: str = Field(default="", max_length=128)


class TopupIn(BaseModel):
    amount_rub: float = Field(gt=0, le=1_000_000)


def raise_billing(exc: BillingError) -> None:
    status = {
        "offer": 403,
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
               u.offer_accepted_at, k.prefix AS key_prefix
        FROM users u
        LEFT JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL
        WHERE u.telegram_id = %s
        """,
        (telegram_id,),
    ).fetchone()


def _public(row: dict) -> dict:
    price = usd_price_rub()
    return {
        "id": row["id"],
        "telegram_id": row["telegram_id"],
        "balance_usd": float(row["balance_usd"]),
        "offer_accepted": row["offer_accepted_at"] is not None,
        "key_prefix": row["key_prefix"] or "",
        "has_key": bool(row["key_prefix"]),
        "offer_url": offer_url(),
        "usd_price_rub": float(price),
        "yookassa_enabled": yookassa_enabled() and bool(bot_start_url()),
    }


def _user_or_404(conn, telegram_id: int) -> dict:
    row = _profile(conn, telegram_id)
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return row


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
        return _public(_user_or_404(conn, body.telegram_id))


@router.get("/users/{telegram_id}")
def get_user(telegram_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        user_id = int(row["id"])
    sync_user(user_id)
    with pool.connection() as conn:
        return _public(_user_or_404(conn, telegram_id))


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
        return _public(_user_or_404(conn, telegram_id))


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
    if amount_rub < 1:
        raise HTTPException(status_code=402, detail="empty")
    amount_usd = rub_to_usd(amount_rub)
    if amount_usd <= 0:
        raise HTTPException(status_code=402, detail="empty")
    kopecks = int((amount_rub * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
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
            SELECT payment_id, status
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
    return {"status": status, "balance_usd": float(fresh["balance_usd"])}


@router.post("/users/{telegram_id}/keys")
def create_key(telegram_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        user_id = int(row["id"])
    try:
        return issue_key(user_id, telegram_id)
    except BillingError as exc:
        raise_billing(exc)


@router.post("/users/{telegram_id}/keys/reissue")
def rotate_key(telegram_id: int) -> dict:
    with pool.connection() as conn:
        row = _user_or_404(conn, telegram_id)
        user_id = int(row["id"])
    try:
        return reissue_key(user_id, telegram_id)
    except BillingError as exc:
        raise_billing(exc)
