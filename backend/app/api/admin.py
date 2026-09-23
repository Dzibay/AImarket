from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import check_password, make_token, require_admin
from app.billing import BillingError, add_usd
from app.db import pool
from app.payments import settle_payment
from app.yookassa import YooKassaError
from app.money import usd_price_rub
from app.settings_store import get_setting, offer_url, public_base_url, set_setting
from app.upstream import UpstreamError, upstream

router = APIRouter()

_TEXT_KEYS = (
    "public_base_url",
    "usd_price_rub",
    "payment_details",
    "seller_name",
    "seller_inn",
    "seller_email",
    "offer_text",
)


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class SettingsIn(BaseModel):
    public_base_url: str = Field(default="", max_length=300)
    usd_price_rub: str = Field(default="", max_length=32)
    payment_details: str = Field(default="", max_length=4000)
    seller_name: str = Field(default="", max_length=200)
    seller_inn: str = Field(default="", max_length=32)
    seller_email: str = Field(default="", max_length=200)
    offer_text: str = Field(default="", max_length=20000)
    router_root_key: str = Field(default="", max_length=300)


class CreditIn(BaseModel):
    amount_usd: float = Field(gt=0, le=100000)


def _settings_payload() -> dict:
    root = get_setting("router_root_key")
    supplier = None
    supplier_error = ""
    if root:
        try:
            supplier = float(upstream.supplier_balance_usd())
        except UpstreamError as exc:
            supplier_error = exc.message
    return {
        "public_base_url": public_base_url(),
        "offer_url": offer_url(),
        "usd_price_rub": str(usd_price_rub()) if usd_price_rub() > 0 else get_setting("usd_price_rub"),
        "payment_details": get_setting("payment_details"),
        "seller_name": get_setting("seller_name"),
        "seller_inn": get_setting("seller_inn"),
        "seller_email": get_setting("seller_email"),
        "offer_text": get_setting("offer_text"),
        "router_root_key_set": bool(root),
        "router_root_key_hint": root[-4:] if len(root) >= 8 else "",
        "supplier_balance_usd": supplier,
        "supplier_error": supplier_error,
    }


@router.post("/login")
def login(body: LoginIn) -> dict:
    if not check_password(body.password):
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"token": make_token()}


@router.get("/settings", dependencies=[Depends(require_admin)])
def read_settings() -> dict:
    return _settings_payload()


@router.put("/settings", dependencies=[Depends(require_admin)])
def write_settings(body: SettingsIn) -> dict:
    price = body.usd_price_rub.strip().replace(",", ".")
    if price:
        try:
            if Decimal(price) < 0:
                raise HTTPException(status_code=422, detail="price")
        except Exception as exc:
            raise HTTPException(status_code=422, detail="price") from exc
    values = {
        "public_base_url": body.public_base_url.strip().rstrip("/"),
        "usd_price_rub": price,
        "payment_details": body.payment_details.strip(),
        "seller_name": body.seller_name.strip(),
        "seller_inn": body.seller_inn.strip(),
        "seller_email": body.seller_email.strip(),
        "offer_text": body.offer_text.strip(),
    }
    for key in _TEXT_KEYS:
        set_setting(key, values[key])
    root = body.router_root_key.strip()
    if root:
        set_setting("router_root_key", root)
        upstream.clear_session()
    return _settings_payload()


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users() -> dict:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.telegram_id, u.username, u.first_name, u.balance_usd,
                   u.offer_accepted_at, k.prefix
            FROM users u
            LEFT JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL
            ORDER BY u.id DESC
            LIMIT 300
            """
        ).fetchall()
    return {
        "items": [
            {
                "id": row["id"],
                "telegram_id": row["telegram_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "balance_usd": float(row["balance_usd"]),
                "offer_accepted": row["offer_accepted_at"] is not None,
                "key_prefix": row["prefix"] or "",
            }
            for row in rows
        ]
    }


@router.post("/users/{user_id}/credit", dependencies=[Depends(require_admin)])
def credit_user(user_id: int, body: CreditIn) -> dict:
    amount = Decimal(str(body.amount_usd)).quantize(Decimal("0.01"))
    try:
        balance = add_usd(user_id, amount, "credit", "начисление из админки")
    except BillingError as exc:
        status = 409 if exc.code == "supplier" else 502
        raise HTTPException(status_code=status, detail=exc.code) from exc
    return {"balance_usd": float(balance)}


@router.get("/topups", dependencies=[Depends(require_admin)])
def list_topups() -> dict:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.amount_kopecks, t.amount_usd, t.status, t.created_at,
                   u.telegram_id, u.username, u.first_name
            FROM topups t
            JOIN users u ON u.id = t.user_id
            ORDER BY t.id DESC
            LIMIT 200
            """
        ).fetchall()
    return {
        "items": [
            {
                "id": row["id"],
                "telegram_id": row["telegram_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "amount_rub": row["amount_kopecks"] / 100,
                "amount_usd": float(row["amount_usd"]),
                "status": row["status"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]
    }


@router.post("/topups/{topup_id}/confirm", dependencies=[Depends(require_admin)])
def confirm_topup(topup_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT user_id, amount_usd, amount_kopecks, payment_id, status FROM topups WHERE id = %s",
            (topup_id,),
        ).fetchone()
    if row is None or row["status"] != "pending":
        raise HTTPException(status_code=404, detail="topup")
    if row["payment_id"]:
        try:
            result = settle_payment(str(row["payment_id"]))
        except YooKassaError as exc:
            raise HTTPException(status_code=502, detail="yookassa") from exc
        except BillingError as exc:
            status = 409 if exc.code == "supplier" else 502
            raise HTTPException(status_code=status, detail=exc.code) from exc
        if result not in {"credited", "already"}:
            raise HTTPException(status_code=409, detail="unpaid")
        with pool.connection() as conn:
            balance = conn.execute("SELECT balance_usd FROM users WHERE id = %s", (row["user_id"],)).fetchone()
        return {"balance_usd": float(balance["balance_usd"])}
    try:
        balance = add_usd(
            int(row["user_id"]),
            Decimal(row["amount_usd"]),
            "topup",
            f"заявка {topup_id}",
            int(row["amount_kopecks"]),
        )
    except BillingError as exc:
        status = 409 if exc.code == "supplier" else 502
        raise HTTPException(status_code=status, detail=exc.code) from exc
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE topups
            SET status = 'paid', decided_at = NOW()
            WHERE id = %s AND status = 'pending'
            """,
            (topup_id,),
        )
    return {"balance_usd": float(balance)}


@router.post("/topups/{topup_id}/reject", dependencies=[Depends(require_admin)])
def reject_topup(topup_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            """
            UPDATE topups
            SET status = 'rejected', decided_at = NOW()
            WHERE id = %s AND status = 'pending'
            RETURNING id
            """,
            (topup_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topup")
    return {"ok": True}
