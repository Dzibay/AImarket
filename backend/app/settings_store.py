import threading
import time
from decimal import Decimal

from app.config import settings
from app.db import pool

# Кэш настроек в памяти процесса: убирает десятки SELECT на /web/me и /web/config.
_lock = threading.Lock()
_cache: dict[str, str] | None = None
_cache_loaded_at = 0.0
# Короткий TTL на случай нескольких воркеров; в своём процессе set_setting обновляет сразу.
_CACHE_TTL_SEC = 15.0


def invalidate_settings_cache() -> None:
    global _cache, _cache_loaded_at
    with _lock:
        _cache = None
        _cache_loaded_at = 0.0


def _fetch_all_settings() -> dict[str, str]:
    with pool.connection() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    return {str(row["key"]): str(row["value"] or "") for row in rows}


def _ensure_cache() -> dict[str, str]:
    global _cache, _cache_loaded_at
    now = time.monotonic()
    with _lock:
        if _cache is not None and (now - _cache_loaded_at) < _CACHE_TTL_SEC:
            return _cache
    # SELECT вне лока — иначе все get_setting ждут одну загрузку под мьютексом.
    fresh = _fetch_all_settings()
    with _lock:
        _cache = fresh
        _cache_loaded_at = time.monotonic()
        return _cache


def get_setting(key: str, default: str = "") -> str:
    cache = _ensure_cache()
    with _lock:
        if key not in cache:
            return default
        return cache[key]


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
    with _lock:
        if _cache is None:
            return
        _cache[key] = value


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


def cookies_url() -> str:
    base = public_base_url()
    return f"{base}/cookies" if base else ""


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
