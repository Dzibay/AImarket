import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field

from app.auth import check_password, make_token, require_admin
from app.billing import BillingError, add_usd
from app.db import pool
from app.money import units_to_usd, usd_price_rub
from app.settings_store import get_setting, offer_url, public_base_url, set_setting
from app.upstream import UpstreamError, upstream

router = APIRouter()
log = logging.getLogger("app.admin")
_MSK = ZoneInfo("Europe/Moscow")

_TEXT_KEYS = (
    "public_base_url",
    "usd_price_rub",
    "offer_email",
    "offer_date",
)


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class SettingsIn(BaseModel):
    public_base_url: str = Field(default="", max_length=300)
    usd_price_rub: str = Field(default="", max_length=32)
    offer_email: str = Field(default="", max_length=200)
    offer_date: str = Field(default="", max_length=32)
    router_root_key: str = Field(default="", max_length=300)


class CreditIn(BaseModel):
    amount_usd: float = Field(gt=0, le=100000)


class LedgerIn(BaseModel):
    user_id: int = Field(gt=0)
    kind: str = Field(min_length=1, max_length=32)
    amount_usd: float = Field(gt=0, le=1_000_000)
    amount_rub: float = Field(default=0, ge=0, le=100_000_000)
    note: str = Field(default="", max_length=300)


_LEDGER_KINDS = {"topup", "credit", "spend", "adjust"}


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
        "offer_email": get_setting("offer_email") or get_setting("seller_email"),
        "offer_date": get_setting("offer_date"),
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
    offer_date = body.offer_date.strip()
    if offer_date:
        try:
            date.fromisoformat(offer_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="offer_date") from exc
    values = {
        "public_base_url": body.public_base_url.strip().rstrip("/"),
        "usd_price_rub": price,
        "offer_email": body.offer_email.strip(),
        "offer_date": offer_date,
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
    stamp = datetime.now(_MSK).strftime("%Y-%m-%d %H:%M:%S")
    try:
        balance = add_usd(user_id, amount, "credit", f"начисление из админки {stamp}")
    except BillingError as exc:
        status = 409 if exc.code == "supplier" else 502
        raise HTTPException(status_code=status, detail=exc.code) from exc
    return {"balance_usd": float(balance)}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
def delete_user(user_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="user")
        keys = conn.execute(
            """
            SELECT upstream_id
            FROM api_keys
            WHERE user_id = %s AND revoked_at IS NULL AND upstream_id IS NOT NULL
            """,
            (user_id,),
        ).fetchall()
    for key in keys:
        token_id = int(key["upstream_id"])
        try:
            upstream.delete_key(token_id)
        except UpstreamError as exc:
            text = exc.message.lower()
            if "404" in text or "not found" in text or "не найден" in text:
                continue
            log.warning("не удалось удалить ключ %s: %s", token_id, exc.message)
            raise HTTPException(status_code=502, detail="upstream") from exc
    with pool.connection() as conn:
        conn.execute("DELETE FROM usage WHERE user_id = %s", (user_id,))
        conn.execute("DELETE FROM ledger WHERE user_id = %s", (user_id,))
        conn.execute("DELETE FROM topups WHERE user_id = %s", (user_id,))
        conn.execute("DELETE FROM api_keys WHERE user_id = %s", (user_id,))
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
    return {"ok": True}


def _person(row: dict) -> str:
    name = str(row["first_name"] or "").strip()
    handle = f"@{row['username']}" if row["username"] else str(row["telegram_id"])
    return f"{name} {handle}".strip()


def _money(value: object) -> float:
    return float(value or 0)


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value  # type: ignore[return-value]


def _fill_days(start: datetime, days: int, rows: list[dict]) -> dict[date, dict]:
    found = {_as_date(row["day"]): row for row in rows}
    series: dict[object, dict] = {}
    for offset in range(days):
        day = (start + timedelta(days=offset)).date()
        series[day] = found.get(day) or {}
    return series


@router.get("/analytics", dependencies=[Depends(require_admin)])
def analytics(days: int = Query(default=30, ge=7, le=90)) -> dict:
    now = datetime.now(_MSK)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    with pool.connection() as conn:
        money = conn.execute(
            """
            SELECT
                COALESCE(SUM(amount_kopecks) FILTER (
                    WHERE status = 'paid' AND COALESCE(decided_at, created_at) >= %s
                ), 0) AS today_kop,
                COALESCE(SUM(amount_kopecks) FILTER (
                    WHERE status = 'paid' AND COALESCE(decided_at, created_at) >= %s
                ), 0) AS period_kop,
                COALESCE(SUM(amount_usd) FILTER (
                    WHERE status = 'paid' AND COALESCE(decided_at, created_at) >= %s
                ), 0) AS period_usd,
                COUNT(*) FILTER (WHERE created_at >= %s) AS period_all,
                COUNT(*) FILTER (
                    WHERE status = 'paid' AND COALESCE(decided_at, created_at) >= %s
                ) AS period_paid,
                COUNT(DISTINCT user_id) FILTER (
                    WHERE status = 'paid' AND COALESCE(decided_at, created_at) >= %s
                ) AS payers
            FROM topups
            """,
            (today, start, start, start, start, start),
        ).fetchone()
        people = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE offer_accepted_at IS NOT NULL) AS accepted,
                COUNT(*) FILTER (WHERE created_at >= %s) AS fresh
            FROM users
            """,
            (start,),
        ).fetchone()
        keys = conn.execute(
            "SELECT COUNT(*) AS active FROM api_keys WHERE revoked_at IS NULL"
        ).fetchone()
        balances = conn.execute("SELECT COALESCE(SUM(balance_usd), 0) AS total FROM users").fetchone()
        revenue_rows = conn.execute(
            """
            SELECT (COALESCE(decided_at, created_at) AT TIME ZONE 'Europe/Moscow')::date AS day,
                   SUM(amount_kopecks) AS kopecks,
                   SUM(amount_usd) AS usd,
                   COUNT(*) AS payments
            FROM topups
            WHERE status = 'paid' AND COALESCE(decided_at, created_at) >= %s
            GROUP BY 1
            """,
            (start,),
        ).fetchall()
        spend_rows = conn.execute(
            """
            SELECT (created_at AT TIME ZONE 'Europe/Moscow')::date AS day,
                   COALESCE(SUM(quota_units), 0) AS units,
                   COUNT(*) AS requests,
                   COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0) AS completion_tokens
            FROM usage
            WHERE created_at >= %s
            GROUP BY 1
            """,
            (start,),
        ).fetchall()
        spend_now = conn.execute(
            """
            SELECT COALESCE(SUM(quota_units), 0) AS units, COUNT(*) AS requests
            FROM usage
            WHERE created_at >= %s
            """,
            (today,),
        ).fetchone()
        model_rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(model_name, ''), 'без модели') AS model,
                   COALESCE(SUM(quota_units), 0) AS units,
                   COUNT(*) AS requests,
                   COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS tokens
            FROM usage
            WHERE created_at >= %s
            GROUP BY 1
            ORDER BY units DESC
            LIMIT 12
            """,
            (start,),
        ).fetchall()
        spender_rows = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name,
                   COALESCE(SUM(g.quota_units), 0) AS units,
                   COUNT(*) AS requests
            FROM usage g
            JOIN users u ON u.id = g.user_id
            WHERE g.created_at >= %s
            GROUP BY u.id
            ORDER BY units DESC
            LIMIT 8
            """,
            (start,),
        ).fetchall()
        payer_rows = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name,
                   COALESCE(SUM(t.amount_kopecks), 0) AS kopecks,
                   COALESCE(SUM(t.amount_usd), 0) AS usd,
                   COUNT(*) AS payments
            FROM topups t
            JOIN users u ON u.id = t.user_id
            WHERE t.status = 'paid' AND COALESCE(t.decided_at, t.created_at) >= %s
            GROUP BY u.id
            ORDER BY kopecks DESC
            LIMIT 8
            """,
            (start,),
        ).fetchall()
        recent_rows = conn.execute(
            """
            SELECT g.created_at, g.model_name, g.quota_units, g.prompt_tokens, g.completion_tokens,
                   u.telegram_id, u.username, u.first_name
            FROM usage g
            JOIN users u ON u.id = g.user_id
            ORDER BY g.created_at DESC
            LIMIT 15
            """
        ).fetchall()
        status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count, COALESCE(SUM(amount_kopecks), 0) AS kopecks
            FROM topups
            WHERE created_at >= %s
            GROUP BY status
            ORDER BY count DESC
            """,
            (start,),
        ).fetchall()
    supplier = None
    if get_setting("router_root_key"):
        try:
            supplier = float(upstream.supplier_balance_usd())
        except UpstreamError:
            supplier = None
    revenue_days = _fill_days(start, days, revenue_rows)
    spend_days = _fill_days(start, days, spend_rows)
    paid = int(money["period_paid"] or 0)
    period_kop = int(money["period_kop"] or 0)
    return {
        "days": days,
        "revenue_today_rub": int(money["today_kop"] or 0) / 100,
        "revenue_rub": period_kop / 100,
        "revenue_usd": _money(money["period_usd"]),
        "payments": int(money["period_all"] or 0),
        "payments_paid": paid,
        "average_check_rub": (period_kop / 100 / paid) if paid else 0,
        "paying_users": int(money["payers"] or 0),
        "spend_today_usd": float(units_to_usd(int(spend_now["units"] or 0))),
        "requests_today": int(spend_now["requests"] or 0),
        "users": int(people["total"] or 0),
        "users_new": int(people["fresh"] or 0),
        "users_accepted": int(people["accepted"] or 0),
        "keys_active": int(keys["active"] or 0),
        "customer_balance_usd": _money(balances["total"]),
        "supplier_balance_usd": supplier,
        "revenue_by_day": [
            {
                "day": day.isoformat(),
                "rub": int(row.get("kopecks") or 0) / 100,
                "usd": _money(row.get("usd")),
                "payments": int(row.get("payments") or 0),
            }
            for day, row in revenue_days.items()
        ],
        "spend_by_day": [
            {
                "day": day.isoformat(),
                "usd": float(units_to_usd(int(row.get("units") or 0))),
                "requests": int(row.get("requests") or 0),
                "prompt_tokens": int(row.get("prompt_tokens") or 0),
                "completion_tokens": int(row.get("completion_tokens") or 0),
            }
            for day, row in spend_days.items()
        ],
        "models": [
            {
                "model": row["model"],
                "usd": float(units_to_usd(int(row["units"] or 0))),
                "requests": int(row["requests"] or 0),
                "tokens": int(row["tokens"] or 0),
            }
            for row in model_rows
        ],
        "spenders": [
            {
                "name": _person(row),
                "usd": float(units_to_usd(int(row["units"] or 0))),
                "requests": int(row["requests"] or 0),
            }
            for row in spender_rows
        ],
        "payers": [
            {
                "name": _person(row),
                "rub": int(row["kopecks"] or 0) / 100,
                "usd": _money(row["usd"]),
                "payments": int(row["payments"] or 0),
            }
            for row in payer_rows
        ],
        "recent": [
            {
                "at": row["created_at"].isoformat(),
                "name": _person(row),
                "model": row["model_name"] or "без модели",
                "usd": float(units_to_usd(int(row["quota_units"] or 0))),
                "tokens": int(row["prompt_tokens"] or 0) + int(row["completion_tokens"] or 0),
            }
            for row in recent_rows
        ],
        "statuses": [
            {"status": row["status"], "count": int(row["count"]), "rub": int(row["kopecks"] or 0) / 100}
            for row in status_rows
        ],
    }


def _ledger_check(conn) -> dict:
    book = conn.execute(
        """
        SELECT
            COALESCE(SUM(amount_usd) FILTER (WHERE kind <> 'spend'), 0)
                - COALESCE(SUM(amount_usd) FILTER (WHERE kind = 'spend'), 0) AS net_usd,
            COALESCE(SUM(amount_usd) FILTER (WHERE kind = 'topup'), 0) AS topup_usd,
            COALESCE(SUM(amount_kopecks) FILTER (WHERE kind = 'topup'), 0) AS topup_kop
        FROM ledger
        """
    ).fetchone()
    balances = conn.execute("SELECT COALESCE(SUM(balance_usd), 0) AS total FROM users").fetchone()
    paid = conn.execute(
        """
        SELECT COALESCE(SUM(amount_usd), 0) AS usd, COALESCE(SUM(amount_kopecks), 0) AS kop
        FROM topups
        WHERE status = 'paid'
        """
    ).fetchone()
    net = Decimal(book["net_usd"])
    customer = Decimal(balances["total"])
    topup_usd = Decimal(book["topup_usd"])
    paid_usd = Decimal(paid["usd"])
    topup_rub = Decimal(int(book["topup_kop"] or 0)) / Decimal(100)
    paid_rub = Decimal(int(paid["kop"] or 0)) / Decimal(100)
    balance_diff = (customer - net).quantize(Decimal("0.0001"))
    payment_diff_usd = (paid_usd - topup_usd).quantize(Decimal("0.0001"))
    payment_diff_rub = (paid_rub - topup_rub).quantize(Decimal("0.01"))
    return {
        "balances_usd": float(customer),
        "ledger_net_usd": float(net),
        "balance_diff_usd": float(balance_diff),
        "balance_ok": balance_diff == 0,
        "payments_usd": float(paid_usd),
        "ledger_topup_usd": float(topup_usd),
        "payments_diff_usd": float(payment_diff_usd),
        "payments_rub": float(paid_rub),
        "ledger_topup_rub": float(topup_rub),
        "payments_diff_rub": float(payment_diff_rub),
        "payments_ok": payment_diff_usd == 0 and payment_diff_rub == 0,
    }


@router.get("/ledger", dependencies=[Depends(require_admin)])
def list_ledger() -> dict:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT l.id, l.user_id, l.kind, l.note, l.amount_usd, l.amount_kopecks, l.created_at,
                   u.telegram_id, u.username, u.first_name
            FROM ledger l
            JOIN users u ON u.id = l.user_id
            ORDER BY l.id DESC
            LIMIT 200
            """
        ).fetchall()
        check = _ledger_check(conn)
    return {
        "check": check,
        "items": [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "kind": row["kind"],
                "note": row["note"],
                "amount_usd": float(row["amount_usd"]),
                "amount_rub": int(row["amount_kopecks"] or 0) / 100,
                "telegram_id": row["telegram_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/ledger", dependencies=[Depends(require_admin)])
def create_ledger(body: LedgerIn) -> dict:
    kind = body.kind.strip()
    if kind not in _LEDGER_KINDS:
        raise HTTPException(status_code=400, detail="kind")
    amount = Decimal(str(body.amount_usd)).quantize(Decimal("0.0001"))
    kopecks = int((Decimal(str(body.amount_rub)) * 100).quantize(Decimal("1")))
    note = body.note.strip()
    with pool.connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE id = %s", (body.user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="user")
        try:
            row = conn.execute(
                """
                INSERT INTO ledger (user_id, amount_kopecks, kind, note, amount_usd)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (body.user_id, kopecks, kind, note, amount),
            ).fetchone()
        except UniqueViolation as exc:
            raise HTTPException(status_code=409, detail="duplicate") from exc
    return {"id": row["id"]}


@router.delete("/ledger/{entry_id}", dependencies=[Depends(require_admin)])
def delete_ledger(entry_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute("DELETE FROM ledger WHERE id = %s RETURNING id", (entry_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="ledger")
    return {"ok": True}


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
