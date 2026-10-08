import logging
from decimal import Decimal

from app.billing import BillingError, add_usd, issue_key
from app.db import pool
from app.telegram_link import notify_payment
from app.yookassa import YooKassaError, get_payment

log = logging.getLogger("app.payments")


def ensure_web_key(user_id: int) -> bool:
    """Выпускает ключ пользователю сайта после первой оплаты. True — ключ есть."""
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT u.telegram_id, u.balance_usd, u.blocked_at,
                   EXISTS (
                       SELECT 1 FROM api_keys k
                       WHERE k.user_id = u.id AND k.revoked_at IS NULL AND k.upstream_id IS NOT NULL
                   ) AS has_key
            FROM users u WHERE u.id = %s
            """,
            (user_id,),
        ).fetchone()
    if row is None or row["blocked_at"] is not None:
        return False
    if row["has_key"]:
        return True
    if Decimal(row["balance_usd"]) <= 0:
        return False
    try:
        issue_key(user_id, int(row["telegram_id"]) if row["telegram_id"] else None)
    except BillingError as exc:
        log.warning("не удалось выпустить ключ пользователю сайта %s: %s", user_id, exc.code)
        return False
    return True


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
            SELECT t.id, t.user_id, t.amount_kopecks, t.amount_usd, t.bonus_usd, t.status, t.payment_id,
                   t.return_token_hash, u.telegram_id, u.email
            FROM topups t
            JOIN users u ON u.id = t.user_id
            WHERE t.id = %s
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
    if row["status"] == "paid":
        return "already"
    bonus = Decimal(row["bonus_usd"] or 0)
    credited_usd = Decimal(row["amount_usd"]) + bonus
    try:
        balance = add_usd(
            int(row["user_id"]),
            credited_usd,
            "topup",
            f"ЮKassa {payment_id}",
            int(row["amount_kopecks"]),
        )
    except BillingError:
        raise
    with pool.connection() as conn:
        credited = conn.execute(
            """
            UPDATE topups
            SET status = 'paid', decided_at = COALESCE(decided_at, NOW())
            WHERE id = %s AND status = 'pending'
            RETURNING id
            """,
            (topup_id,),
        ).fetchone()
    if credited is None:
        return "already"
    try:
        from app.finance import record_yookassa_payment

        record_yookassa_payment(
            topup_id=topup_id,
            amount_kopecks=int(row["amount_kopecks"]),
            amount_usd=Decimal(row["amount_usd"]),
            payment_id=str(payment_id),
        )
    except Exception:
        log.exception("не удалось записать оплату %s в финансы", topup_id)
    user_id = int(row["user_id"])
    # Оплата с сайта: ключ — это и доступ к API, и пароль в кабинет, выпускаем сразу и шлём письмо.
    if row["return_token_hash"]:
        first_key = not _has_active_key(user_id)
        ensure_web_key(user_id)
        if row["email"]:
            from app.mailer import send_payment_email

            send_payment_email(
                user_id,
                amount_usd=Decimal(row["amount_usd"]),
                bonus_usd=bonus,
                balance_usd=balance,
                first_key=first_key,
            )
    telegram_id = int(row["telegram_id"] or 0)
    if telegram_id > 0:
        notify_payment(telegram_id, credited_usd, balance, has_key=_has_active_key(user_id))
    return "credited"


def _has_active_key(user_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM api_keys WHERE user_id = %s AND revoked_at IS NULL LIMIT 1",
            (user_id,),
        ).fetchone()
    return row is not None
