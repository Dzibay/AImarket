import json
import logging
import threading
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

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


def notify_payment(telegram_id: int, amount_usd: Decimal, balance_usd: Decimal) -> None:
    """Сообщает пользователю, что оплата зачислена. Ошибка доставки не отменяет платёж."""
    token = settings.telegram_bot_token.strip()
    if not token or telegram_id <= 0:
        log.warning("уведомление об оплате не отправлено: нет токена бота или telegram id")
        return
    caption = (
        "<b>Оплата прошла</b>\n\n"
        f"Зачислено <b>${amount_usd:.2f}</b>\n"
        f"Баланс <b>${balance_usd:.2f}</b>"
    )
    keyboard = {
        "inline_keyboard": [[{"text": "Личный кабинет", "callback_data": "cabinet", "style": "success"}]]
    }
    photo = _payment_photo()
    try:
        if photo:
            _telegram(
                token,
                "sendPhoto",
                {
                    "chat_id": str(telegram_id),
                    "caption": caption,
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard, ensure_ascii=False),
                },
                file_field="photo",
                filename="pay.png",
                file_bytes=photo,
            )
        else:
            _telegram(
                token,
                "sendMessage",
                {
                    "chat_id": str(telegram_id),
                    "text": caption,
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard, ensure_ascii=False),
                },
            )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("не удалось отправить уведомление об оплате %s: %s", telegram_id, exc)


def _payment_photo() -> bytes:
    candidates = (
        Path(__file__).resolve().parent / "images" / "pay.png",
        Path(__file__).resolve().parents[2] / "bot" / "app" / "images" / "pay.png",
    )
    for path in candidates:
        if path.is_file():
            return path.read_bytes()
    log.warning("картинка оплаты не найдена")
    return b""


def _telegram(
    token: str,
    method: str,
    fields: dict[str, str],
    *,
    file_field: str = "",
    filename: str = "",
    file_bytes: bytes = b"",
) -> None:
    boundary = "----aimarket-boundary"
    body = bytearray()
    for name, value in fields.items():
        body.extend(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode()
        )
    if file_field and file_bytes:
        body.extend(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
                "Content-Type: image/png\r\n\r\n"
            ).encode()
        )
        body.extend(file_bytes)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "aimarket",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode())
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise urllib.error.URLError(str(payload)[:300])


def bot_start_url(payload: str = "") -> str:
    username = bot_username()
    if not username:
        return ""
    if payload:
        return f"https://t.me/{username}?start={payload}"
    return f"https://t.me/{username}"
