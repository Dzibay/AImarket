from decimal import Decimal

from app.config import settings
from app.db import pool


def get_setting(key: str, default: str = "") -> str:
    with pool.connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = %s", (key,)).fetchone()
    if row is None or row["value"] is None:
        return default
    return str(row["value"])


def set_setting(key: str, value: str) -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            (key, value),
        )


def public_base_url() -> str:
    stored = get_setting("public_base_url").strip().rstrip("/")
    if stored:
        return stored
    return settings.public_base_url.strip().rstrip("/")


def offer_url() -> str:
    base = public_base_url()
    return f"{base}/offer" if base else ""


def bootstrap_settings() -> None:
    if not get_setting("router_root_key") and settings.router_root_key:
        set_setting("router_root_key", settings.router_root_key)
    if not get_setting("usd_price_rub") and settings.usd_price_kopecks > 0:
        rub = Decimal(settings.usd_price_kopecks) / Decimal(100)
        set_setting("usd_price_rub", f"{rub:.2f}")
    if not get_setting("public_base_url") and settings.public_base_url:
        set_setting("public_base_url", settings.public_base_url.strip().rstrip("/"))
