import json
import logging
import threading
import urllib.error
import urllib.request

from app.config import settings

log = logging.getLogger("app.telegram_link")
_lock = threading.Lock()
_cached_username = ""


def bot_username() -> str:
    configured = settings.telegram_bot_username.strip().lstrip("@")
    if configured:
        return configured
    global _cached_username
    with _lock:
        if _cached_username:
            return _cached_username
        token = settings.telegram_bot_token.strip()
        if not token:
            return ""
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            headers={"User-Agent": "aimarket"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            log.warning("не удалось узнать имя бота: %s", exc)
            return ""
        username = ""
        if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
            username = str(payload["result"].get("username") or "").strip()
        if username:
            _cached_username = username
        return username


def bot_start_url(payload: str = "") -> str:
    username = bot_username()
    if not username:
        return ""
    if payload:
        return f"https://t.me/{username}?start={payload}"
    return f"https://t.me/{username}"
