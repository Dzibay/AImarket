import logging
import time
from decimal import Decimal

from app.db import pool
from app.telegram_link import (
    notify_limit_exhausted,
    notify_low_balance,
    notify_spend,
)

log = logging.getLogger("app.notifications")

LOW_BALANCE_USD = Decimal("5")
_TOGGLE_KEYS = {
    "spend": "notify_spend",
    "low_balance": "notify_low_balance",
    "limit_exhausted": "notify_limit_exhausted",
    "topup": "notify_topup",
}


def preferences_row(row: dict | None) -> dict:
    if not row:
        return {
            "spend": False,
            "low_balance": True,
            "limit_exhausted": True,
            "topup": True,
        }
    return {
        "spend": bool(row.get("notify_spend")),
        "low_balance": bool(row.get("notify_low_balance")),
        "limit_exhausted": bool(row.get("notify_limit_exhausted")),
        "topup": True,
    }


def get_preferences(user_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT notify_spend, notify_low_balance, notify_limit_exhausted, notify_topup
            FROM users WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
    return preferences_row(row)


def toggle_preference(user_id: int, key: str) -> dict:
    column = _TOGGLE_KEYS.get(key)
    if column is None:
        raise ValueError("unknown")
    if key == "topup":
        return get_preferences(user_id)
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            UPDATE users
            SET {column} = NOT {column}
            WHERE id = %s
            RETURNING notify_spend, notify_low_balance, notify_limit_exhausted, notify_topup
            """,
            (user_id,),
        ).fetchone()
    return preferences_row(row)


def clear_low_balance_alert(user_id: int) -> None:
    with pool.connection() as conn:
        conn.execute(
            "UPDATE users SET low_balance_notified_at = NULL WHERE id = %s",
            (user_id,),
        )


def clear_limit_alert(key_id: int) -> None:
    with pool.connection() as conn:
        conn.execute(
            "UPDATE api_keys SET limit_exhausted_notified_at = NULL WHERE id = %s",
            (key_id,),
        )


def _mask_key_label(secret: str, prefix: str = "") -> str:
    value = secret or prefix
    if len(value) <= 12:
        return value or "API-ключ"
    return f"{value[:8]}...{value[-4:]}"


def process_new_usages(
    user_id: int,
    telegram_id: int,
    key_id: int | None,
    usages: list[dict],
    balance_usd: Decimal,
) -> None:
    if not usages or telegram_id <= 0:
        return
    prefs = get_preferences(user_id)
    if not prefs["spend"]:
        return
    key_label = "API-ключ"
    if key_id is not None:
        with pool.connection() as conn:
            key = conn.execute(
                "SELECT prefix, secret FROM api_keys WHERE id = %s",
                (key_id,),
            ).fetchone()
        if key is not None:
            key_label = _mask_key_label(str(key.get("secret") or ""), str(key.get("prefix") or ""))
    running_balance = balance_usd.quantize(Decimal("0.0001"))
    for item in usages:
        amount_usd = Decimal(str(item.get("amount_usd") or 0)).quantize(Decimal("0.0001"))
        try:
            notify_spend(
                telegram_id,
                model=str(item.get("model_name") or "—"),
                prompt_tokens=int(item.get("prompt_tokens") or 0),
                completion_tokens=int(item.get("completion_tokens") or 0),
                amount_usd=amount_usd,
                balance_usd=running_balance,
                key_label=key_label,
            )
        except Exception:
            log.exception("уведомление о трате user=%s", user_id)
        else:
            running_balance = max(Decimal(0), running_balance - amount_usd).quantize(Decimal("0.0001"))
            time.sleep(0.05)


def process_balance_alerts(
    user_id: int,
    telegram_id: int,
    key_id: int | None,
    balance_usd: Decimal,
    limit_usd: Decimal,
    *,
    key_label: str = "API-ключ",
) -> None:
    if telegram_id <= 0:
        return
    prefs = get_preferences(user_id)
    balance = balance_usd.quantize(Decimal("0.0001"))

    if balance >= LOW_BALANCE_USD:
        clear_low_balance_alert(user_id)

    if prefs["low_balance"] and Decimal("0") < balance < LOW_BALANCE_USD:
        with pool.connection() as conn:
            row = conn.execute(
                """
                SELECT low_balance_notified_at
                FROM users
                WHERE id = %s AND blocked_at IS NULL
                """,
                (user_id,),
            ).fetchone()
        if row is not None and row.get("low_balance_notified_at") is None:
            try:
                notify_low_balance(telegram_id, balance)
            except Exception:
                log.exception("уведомление о низком балансе user=%s", user_id)
            else:
                with pool.connection() as conn:
                    conn.execute(
                        "UPDATE users SET low_balance_notified_at = NOW() WHERE id = %s",
                        (user_id,),
                    )

    if key_id is None:
        return

    if balance > 0:
        clear_limit_alert(key_id)
        return

    if not prefs["limit_exhausted"]:
        return

    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT limit_exhausted_notified_at
            FROM api_keys
            WHERE id = %s AND revoked_at IS NULL
            """,
            (key_id,),
        ).fetchone()
    if row is None or row.get("limit_exhausted_notified_at") is not None:
        return
    try:
        notify_limit_exhausted(telegram_id, key_label, limit_usd)
    except Exception:
        log.exception("уведомление об исчерпании лимита user=%s key=%s", user_id, key_id)
    else:
        with pool.connection() as conn:
            conn.execute(
                "UPDATE api_keys SET limit_exhausted_notified_at = NOW() WHERE id = %s",
                (key_id,),
            )


def check_low_balance_users() -> None:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.telegram_id, u.balance_usd
            FROM users u
            WHERE u.notify_low_balance
              AND u.blocked_at IS NULL
              AND u.balance_usd > 0
              AND u.balance_usd < %s
              AND u.low_balance_notified_at IS NULL
            """,
            (LOW_BALANCE_USD,),
        ).fetchall()
    for row in rows:
        process_balance_alerts(
            int(row["id"]),
            int(row["telegram_id"] or 0),
            None,
            Decimal(row["balance_usd"]),
            Decimal("0"),
        )
