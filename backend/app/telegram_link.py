import html
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

from app.config import settings
from app.money import usd_price_rub

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


def notify_offer_reminder(
    telegram_id: int,
    *,
    privacy_url: str = "",
    consent_url: str = "",
    offer_url: str = "",
) -> bool:
    """Напоминание принять документы. Возвращает True, если попытка отправки была."""
    token = settings.telegram_bot_token.strip()
    if not token or telegram_id <= 0:
        log.warning("напоминание об оферте не отправлено: нет токена бота или telegram id")
        return False
    price = usd_price_rub()
    price_text = f"{float(price):.2f}".rstrip("0").rstrip(".") if price > 0 else "—"
    caption = (
        f"⚠️ От использования ИИ за <b>{price_text} ₽</b> вас отделяет "
        "принятие условий пользования ботом"
    )
    rows: list[list[dict]] = []
    doc_row: list[dict] = []
    if privacy_url:
        doc_row.append({"text": "📜 Политика", "url": privacy_url})
    if consent_url:
        doc_row.append({"text": "📋 Согласие", "url": consent_url})
    if offer_url:
        doc_row.append({"text": "📄 Оферта", "url": offer_url})
    if doc_row:
        rows.append(doc_row)
    rows.append([{"text": "✅ Принять все условия", "callback_data": "offer:yes", "style": "success"}])
    keyboard = {"inline_keyboard": rows}
    photo = _offer_photo()
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
                filename="offer.png",
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
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("не удалось отправить напоминание об оферте %s: %s", telegram_id, exc)
        return True


def notify_payment(
    telegram_id: int,
    amount_usd: Decimal,
    balance_usd: Decimal,
    *,
    has_key: bool = False,
) -> None:
    """Сообщает пользователю, что оплата зачислена. Ошибка доставки не отменяет платёж."""
    _ = has_key
    token = settings.telegram_bot_token.strip()
    if not token or telegram_id <= 0:
        log.warning("уведомление об оплате не отправлено: нет токена бота или telegram id")
        return
    text = (
        "✅ <b>Баланс пополнен</b>\n\n"
        f"💵 Зачислено: <b>${amount_usd:.2f}</b>\n"
        f"💰 Текущий баланс: <b>${balance_usd:.2f}</b>"
    )
    _send_text(token, telegram_id, text)


def notify_spend(
    telegram_id: int,
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    amount_usd: Decimal,
    balance_usd: Decimal,
    key_label: str,
) -> None:
    token = settings.telegram_bot_token.strip()
    if not token or telegram_id <= 0:
        return
    text = (
        "⚡ <b>Использование API</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Модель: {html.escape(model)}\n"
        f"📈 Токены: {_fmt_tokens(prompt_tokens)} in / {_fmt_tokens(completion_tokens)} out\n"
        f"💸 Стоимость: ${_money_small(amount_usd)}\n"
        f"💰 Баланс: ${_money_small(balance_usd)}\n"
        f"🔑 Ключ: «{html.escape(key_label)}»\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    _send_text(token, telegram_id, text)


def notify_low_balance(telegram_id: int, balance_usd: Decimal) -> None:
    token = settings.telegram_bot_token.strip()
    if not token or telegram_id <= 0:
        return
    text = (
        "⚠️ <b>Низкий баланс</b>\n\n"
        f"💰 Ваш баланс: <b>${balance_usd:.2f}</b>\n\n"
        "Рекомендуем пополнить, чтобы работа не остановилась"
    )
    keyboard = {
        "inline_keyboard": [[{"text": "💳 Пополнить баланс", "callback_data": "topup"}]]
    }
    _send_text(token, telegram_id, text, keyboard=keyboard)


def notify_limit_exhausted(telegram_id: int, key_label: str, limit_usd: Decimal) -> None:
    token = settings.telegram_bot_token.strip()
    if not token or telegram_id <= 0:
        return
    text = (
        f"🛑 Ключ «{html.escape(key_label)}» достиг лимита трат (<b>${limit_usd:.2f}</b>)\n"
        "🚫 Запросы с этим ключом приостановлены"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Изменить лимит", "callback_data": "keys"},
                {"text": "💳 Пополнить баланс", "callback_data": "topup"},
            ]
        ]
    }
    _send_text(token, telegram_id, text, keyboard=keyboard)


def _fmt_tokens(value: int) -> str:
    return f"{int(value):,}".replace(",", ",")


def _money_small(value: Decimal) -> str:
    amount = Decimal(value)
    if amount >= Decimal("0.01"):
        return f"{amount:.2f}"
    return f"{amount:.4f}"


def _send_text(
    token: str,
    telegram_id: int,
    text: str,
    *,
    keyboard: dict | None = None,
) -> None:
    payload: dict[str, str] = {
        "chat_id": str(telegram_id),
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    try:
        _telegram(token, "sendMessage", payload)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        log.warning("не удалось отправить уведомление %s: %s", telegram_id, exc)


def _bot_image(name: str) -> bytes:
    candidates = (
        Path(__file__).resolve().parent / "images" / name,
        Path(__file__).resolve().parents[2] / "bot" / "app" / "images" / name,
    )
    for path in candidates:
        if path.is_file():
            return path.read_bytes()
    return b""


def _payment_photo() -> bytes:
    photo = _bot_image("pay.png")
    if not photo:
        log.warning("картинка оплаты не найдена")
    return photo


def _offer_photo() -> bytes:
    photo = _bot_image("offer.png")
    if not photo:
        log.warning("картинка оферты не найдена")
    return photo


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
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        else:
            if not isinstance(payload, dict) or not payload.get("ok"):
                raise urllib.error.URLError(str(payload)[:300])
            return
    if last_error is not None:
        raise last_error


def bot_start_url(payload: str = "") -> str:
    username = bot_username()
    if not username:
        return ""
    if payload:
        return f"https://t.me/{username}?start={payload}"
    return f"https://t.me/{username}"
