"""Личный кабинет на сайте: оплата без Telegram, вход по API-ключу.

Поток новой покупки:
  1. POST /checkout — создаём пользователя (почта), заявку topups и платёж ЮKassa.
     В return_url кладём одноразовый токен; его хэш хранится в topups.return_token_hash.
  2. ЮKassa возвращает человека на /pay/return/{topup}/{token} (страница Vue).
  3. POST /payments/return — сверяем токен, подтверждаем платёж, выпускаем ключ в router.cheap,
     выдаём сессию кабинета. Ключ одновременно и доступ к API, и пароль для входа.
"""

import hmac
import logging
import re
import secrets
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.billing import BillingError, describe_key, reissue_key, sync_user, upstream_base
from app.datetime_util import iso_utc
from app.db import pool
from app.history import HISTORY_PAGE, history_payload
from app.mailer import enabled as mail_enabled
from app.money import bonus_tiers, min_topup_rub, min_topup_usd, rub_to_usd, topup_bonus, usd_price_rub
from app.payments import ensure_web_key, settle_payment
from app.settings_store import get_setting, public_base_url, support_username
from app.telegram_link import bot_start_url
from app.usage_stats import usage_period_stats
from app.web_auth import key_hash, make_session, require_web_user
from app.yookassa import YooKassaError, create_payment, enabled as yookassa_enabled

router = APIRouter(tags=["web"])
log = logging.getLogger("app.web")

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RETURN_TOKEN_TTL = "24 hours"


class AmountIn(BaseModel):
    amount_usd: float | None = Field(default=None, gt=0, le=100_000)
    amount_rub: float | None = Field(default=None, gt=0, le=10_000_000)


class CheckoutIn(AmountIn):
    email: str = Field(min_length=3, max_length=200)


class ReturnIn(BaseModel):
    topup: int = Field(gt=0)
    token: str = Field(min_length=10, max_length=200)


class LoginIn(BaseModel):
    key: str = Field(min_length=8, max_length=300)


class LinkLoginIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


def _config_payload() -> dict:
    price = usd_price_rub()
    return {
        "usd_price_rub": float(price),
        "min_topup_usd": float(min_topup_usd()),
        "min_topup_rub": float(min_topup_rub()),
        "bonuses": bonus_tiers(),
        "email_enabled": mail_enabled(),
        "sales_open": price > 0 and yookassa_enabled() and bool(public_base_url()),
        "api_base_url": upstream_base(),
        "support_email": (get_setting("offer_email") or get_setting("seller_email")).strip(),
        "support_username": support_username(),
        "bot_url": bot_start_url(),
    }


def _resolve_amount(body: AmountIn) -> tuple[Decimal, Decimal]:
    """Возвращает (рубли к оплате, доллары к зачислению).

    Вводил доллары — рубли округляем вверх до копейки, чтобы зачислить ровно столько.
    Вводил рубли — доллары считаем как в боте (вниз до цента).
    """
    price = usd_price_rub()
    if price <= 0 or not yookassa_enabled() or not public_base_url():
        raise HTTPException(status_code=402, detail="sales-closed")
    if body.amount_usd is not None:
        usd = Decimal(str(body.amount_usd)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rub = (usd * price).quantize(Decimal("0.01"), rounding=ROUND_UP)
    elif body.amount_rub is not None:
        rub = Decimal(str(body.amount_rub)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        usd = rub_to_usd(rub)
    else:
        raise HTTPException(status_code=400, detail="amount")
    if usd < min_topup_usd() or rub < min_topup_rub():
        raise HTTPException(status_code=402, detail="min-topup")
    return rub, usd


def _start_payment(user_id: int, rub: Decimal, usd: Decimal, email: str) -> dict:
    kopecks = int((rub * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    bonus_percent, bonus_usd = topup_bonus(usd)
    token = secrets.token_urlsafe(24)
    with pool.connection() as conn:
        created = conn.execute(
            """
            INSERT INTO topups (user_id, amount_kopecks, amount_usd, bonus_usd, return_token_hash)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, kopecks, usd, bonus_usd, key_hash(token)),
        ).fetchone()
    topup_id = int(created["id"])
    # Путь без query — ЮKassa надёжнее принимает такой return_url, чем длинную строку с ?t=.
    base = public_base_url()
    return_url = f"{base}/pay/return/{topup_id}/{quote(token, safe='')}"
    try:
        payment = create_payment(topup_id, rub, return_url, customer_email=email)
    except YooKassaError as exc:
        with pool.connection() as conn:
            conn.execute("UPDATE topups SET status = 'failed', decided_at = NOW() WHERE id = %s", (topup_id,))
        raise HTTPException(status_code=502, detail="yookassa") from exc
    with pool.connection() as conn:
        conn.execute("UPDATE topups SET payment_id = %s WHERE id = %s", (payment["id"], topup_id))
    return {
        "id": topup_id,
        "amount_rub": float(rub),
        "amount_usd": float(usd),
        "bonus_usd": float(bonus_usd),
        "bonus_percent": float(bonus_percent),
        "pay_url": payment["url"],
    }


def _user_row(user_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT id, telegram_id, email, balance_usd, offer_accepted_at, blocked_at, blocked_reason, created_at
            FROM users WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return row


def _settle_pending(user_id: int) -> None:
    """Досверяет свежие платежи, если человек вернулся в кабинет не через return_url."""
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT payment_id FROM topups
            WHERE user_id = %s AND status = 'pending' AND payment_id IS NOT NULL
              AND created_at >= NOW() - INTERVAL '2 days'
            ORDER BY id DESC LIMIT 3
            """,
            (user_id,),
        ).fetchall()
    for row in rows:
        try:
            settle_payment(str(row["payment_id"]))
        except (YooKassaError, BillingError):
            continue


def _profile(user_id: int) -> dict:
    row = _user_row(user_id)
    blocked = row["blocked_at"] is not None
    key = None
    key_error = ""
    if not blocked:
        if ensure_web_key(user_id):
            sync_user(user_id)
            try:
                key = describe_key(user_id)
            except BillingError as exc:
                key_error = exc.code
    row = _user_row(user_id)
    with pool.connection() as conn:
        stats = usage_period_stats(conn, user_id)
    return {
        "id": int(row["id"]),
        "email": row["email"] or "",
        "balance_usd": float(row["balance_usd"]),
        "blocked": blocked,
        "blocked_reason": row["blocked_reason"] or "",
        "created_at": iso_utc(row["created_at"]),
        "key": key,
        "key_error": key_error,
        "spent_today_usd": stats["spent_today_usd"],
        "spent_month_usd": stats["spent_month_usd"],
        "spent_week_usd": stats["spent_week_usd"],
        "last_request_at": iso_utc(stats["last_request_at"]),
        **_config_payload(),
    }


@router.get("/web/config")
def web_config() -> dict:
    return _config_payload()


@router.post("/web/checkout")
def checkout(body: CheckoutIn) -> dict:
    email = body.email.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=400, detail="email")
    rub, usd = _resolve_amount(body)
    # Нажатие «Оплатить» на сайте — акцепт оферты, политики и согласия (п. 1.2 оферты).
    with pool.connection() as conn:
        created = conn.execute(
            """
            INSERT INTO users (telegram_id, email, offer_accepted_at)
            VALUES (NULL, %s, NOW())
            RETURNING id
            """,
            (email,),
        ).fetchone()
    return _start_payment(int(created["id"]), rub, usd, email)


@router.post("/web/payments/return")
def payment_return(body: ReturnIn) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT t.id, t.user_id, t.status, t.payment_id, t.return_token_hash,
                   t.amount_usd, t.bonus_usd,
                   t.created_at >= NOW() - INTERVAL %s AS fresh
            FROM topups t WHERE t.id = %s
            """,
            (_RETURN_TOKEN_TTL, body.topup),
        ).fetchone()
    if row is None or not row["return_token_hash"]:
        raise HTTPException(status_code=404, detail="topup")
    if not hmac.compare_digest(row["return_token_hash"], key_hash(body.token)):
        raise HTTPException(status_code=403, detail="token")
    if not row["fresh"]:
        raise HTTPException(status_code=410, detail="expired")
    status = str(row["status"])
    if status == "pending" and row["payment_id"]:
        try:
            result = settle_payment(str(row["payment_id"]))
        except (YooKassaError, BillingError) as exc:
            log.warning("возврат с оплаты %s: %s", body.topup, exc)
            result = "pending"
        if result in {"credited", "already"}:
            status = "paid"
    user_id = int(row["user_id"])
    profile = _profile(user_id) if status == "paid" else None
    return {
        "status": status,
        "session": make_session(user_id) if status == "paid" else "",
        "profile": profile,
        "amount_usd": float(row["amount_usd"]),
        "bonus_usd": float(row["bonus_usd"] or 0),
    }


@router.post("/web/login/link")
def login_by_link(body: LinkLoginIn) -> dict:
    """Вход по кнопке из письма — токен хранится хэшем на пользователе, срок ограничен."""
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT id FROM users
            WHERE email_login_hash <> '' AND email_login_hash = %s
              AND email_login_expires_at IS NOT NULL AND email_login_expires_at > NOW()
            """,
            (key_hash(body.token),),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="expired")
    user_id = int(row["id"])
    return {"session": make_session(user_id), "profile": _profile(user_id)}


@router.post("/web/login")
def login(body: LoginIn) -> dict:
    secret = body.key.strip()
    if not secret.startswith("sk-"):
        secret = f"sk-{secret}"
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT user_id FROM api_keys
            WHERE secret_hash = %s AND revoked_at IS NULL
            """,
            (key_hash(secret),),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="key")
    user_id = int(row["user_id"])
    return {"session": make_session(user_id), "profile": _profile(user_id)}


@router.get("/web/me")
def me(user_id: int = Depends(require_web_user)) -> dict:
    _settle_pending(user_id)
    return _profile(user_id)


@router.get("/web/history")
def history(
    filter: str = "all",
    offset: int = 0,
    limit: int = HISTORY_PAGE,
    user_id: int = Depends(require_web_user),
) -> dict:
    _user_row(user_id)
    sync_user(user_id)
    return history_payload(user_id, filter, offset, limit)


@router.post("/web/topups")
def create_topup(body: AmountIn, user_id: int = Depends(require_web_user)) -> dict:
    row = _user_row(user_id)
    if row["blocked_at"] is not None:
        raise HTTPException(status_code=403, detail="blocked")
    rub, usd = _resolve_amount(body)
    with pool.connection() as conn:
        conn.execute(
            "UPDATE users SET offer_accepted_at = COALESCE(offer_accepted_at, NOW()) WHERE id = %s",
            (user_id,),
        )
    return _start_payment(user_id, rub, usd, str(row["email"] or ""))


@router.post("/web/topups/{topup_id}/check")
def check_topup(topup_id: int, user_id: int = Depends(require_web_user)) -> dict:
    with pool.connection() as conn:
        topup = conn.execute(
            "SELECT payment_id, status, amount_usd FROM topups WHERE id = %s AND user_id = %s",
            (topup_id, user_id),
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
    return {"status": status, "amount_usd": float(topup["amount_usd"]), "profile": _profile(user_id)}


@router.post("/web/keys/reissue")
def rotate_key(user_id: int = Depends(require_web_user)) -> dict:
    row = _user_row(user_id)
    try:
        result = reissue_key(user_id, int(row["telegram_id"]) if row["telegram_id"] else None)
    except BillingError as exc:
        status = {"blocked": 403, "offer": 403, "no-key": 409, "empty": 402, "supplier": 409}.get(exc.code, 502)
        raise HTTPException(status_code=status, detail=exc.code) from exc
    return {"secret": result["secret"], "profile": _profile(user_id)}
