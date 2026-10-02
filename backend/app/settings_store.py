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


def normalize_base_url(raw: str) -> str:
    """Абсолютный URL сайта для ЮKassa return_url и ссылок в письмах."""
    url = (raw or "").strip().rstrip("/")
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    # ЮKassa в проде принимает только https; http часто игнорируется → редирект на yookassa.ru.
    if url.startswith("http://") and "localhost" not in url and "127.0.0.1" not in url:
        url = "https://" + url.removeprefix("http://")
    return url


def public_base_url() -> str:
    stored = get_setting("public_base_url").strip()
    if stored:
        return normalize_base_url(stored)
    return normalize_base_url(settings.public_base_url)


def offer_url() -> str:
    base = public_base_url()
    return f"{base}/offer" if base else ""


def privacy_url() -> str:
    base = public_base_url()
    return f"{base}/privacy" if base else ""


def consent_url() -> str:
    base = public_base_url()
    return f"{base}/consent" if base else ""


def support_username() -> str:
    return get_setting("support_username").strip().lstrip("@")


def bootstrap_settings() -> None:
    if not get_setting("router_root_key") and settings.router_root_key:
        set_setting("router_root_key", settings.router_root_key)
    if not get_setting("usd_price_rub") and settings.usd_price_kopecks > 0:
        rub = Decimal(settings.usd_price_kopecks) / Decimal(100)
        set_setting("usd_price_rub", f"{rub:.2f}")
    if not get_setting("public_base_url") and settings.public_base_url:
        set_setting("public_base_url", normalize_base_url(settings.public_base_url))
