import logging
from decimal import Decimal

from app.billing import BillingError, add_usd
from app.db import pool
from app.yookassa import YooKassaError, get_payment

log = logging.getLogger("app.payments")


def settle_payment(payment_id: str) -> str:
    """Сверяет платёж с ЮKassa и один раз зачисляет баланс. Возвращает статус обработки."""
    try:
        payment = get_payment(payment_id)
    except YooKassaError as exc:
        log.warning("не удалось прочитать платёж %s: %s", payment_id, exc.message)
        raise
    if payment.get("status") != "succeeded" or not payment.get("paid"):
        return "pending"
    metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
    try:
        topup_id = int(metadata.get("topup_id") or 0)
    except (TypeError, ValueError):
        return "ignored"
    amount = payment.get("amount") if isinstance(payment.get("amount"), dict) else {}
    if amount.get("currency") != "RUB":
        return "ignored"
    try:
        paid_kopecks = int((Decimal(str(amount.get("value") or "0")) * 100).quantize(Decimal("1")))
    except Exception:
        return "ignored"

    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, amount_kopecks, amount_usd, status, payment_id
            FROM topups
            WHERE id = %s
            """,
            (topup_id,),
        ).fetchone()
    if row is None or str(row["payment_id"] or "") != str(payment.get("id")):
        return "ignored"
    if int(row["amount_kopecks"]) != paid_kopecks:
        log.warning("сумма платежа %s не совпала с заявкой %s", payment_id, topup_id)
        return "ignored"
    if row["status"] == "rejected":
        return "ignored"
    try:
        add_usd(
            int(row["user_id"]),
            Decimal(row["amount_usd"]),
            "topup",
            f"ЮKassa {payment_id}",
            int(row["amount_kopecks"]),
        )
    except BillingError:
        raise
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE topups
            SET status = 'paid', decided_at = COALESCE(decided_at, NOW())
            WHERE id = %s AND status = 'pending'
            """,
            (topup_id,),
        )
    return "credited"
