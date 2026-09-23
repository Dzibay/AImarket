import base64
import json
import logging
import urllib.error
import urllib.request
import uuid
from decimal import Decimal

from app.config import settings

log = logging.getLogger("app.yookassa")
_API = "https://api.yookassa.ru/v3"


class YooKassaError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def enabled() -> bool:
    return bool(settings.yookassa_shop_id.strip() and settings.yookassa_secret_key.strip())


def create_payment(topup_id: int, amount_rub: Decimal, return_url: str) -> dict:
    value = f"{amount_rub.quantize(Decimal('0.01')):.2f}"
    body: dict = {
        "amount": {"value": value, "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": f"Пополнение Aimarket #{topup_id}",
        "metadata": {"topup_id": str(topup_id)},
    }
    receipt_email = settings.yookassa_receipt_email.strip()
    if receipt_email:
        body["receipt"] = {
            "customer": {"email": receipt_email},
            "items": [
                {
                    "description": "Пополнение баланса Aimarket",
                    "quantity": "1.00",
                    "amount": {"value": value, "currency": "RUB"},
                    "vat_code": settings.yookassa_vat_code,
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                }
            ],
        }
    payment = _request(
        "POST",
        "/payments",
        body,
        idempotence_key=str(uuid.uuid5(uuid.NAMESPACE_URL, f"aimarket-topup-{topup_id}")),
    )
    url = (payment.get("confirmation") or {}).get("confirmation_url") or ""
    if not payment.get("id") or not url:
        raise YooKassaError("ЮKassa не вернула ссылку на оплату")
    return {"id": str(payment["id"]), "url": str(url), "status": str(payment.get("status") or "")}


def get_payment(payment_id: str) -> dict:
    payment = _request("GET", f"/payments/{payment_id}")
    if not payment.get("id"):
        raise YooKassaError("платёж ЮKassa не найден")
    return payment


def _request(method: str, path: str, body: dict | None = None, idempotence_key: str = "") -> dict:
    if not enabled():
        raise YooKassaError("ЮKassa не настроена")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(_API + path, data=data, method=method)
    token = base64.b64encode(
        f"{settings.yookassa_shop_id.strip()}:{settings.yookassa_secret_key.strip()}".encode()
    ).decode()
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "aimarket")
    if idempotence_key:
        req.add_header("Idempotence-Key", idempotence_key)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        message = _error_message(raw) or f"ЮKassa {exc.code}"
        log.warning("ЮKassa %s %s -> %s", method, path, message)
        raise YooKassaError(message) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        log.warning("ЮKassa недоступна: %s", exc)
        raise YooKassaError("ЮKassa недоступна") from exc
    return payload if isinstance(payload, dict) else {}


def _error_message(raw: str) -> str:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:180]
    if isinstance(body, dict):
        return str(body.get("description") or body.get("code") or "")[:180]
    return ""
