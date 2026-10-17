"""Учёт остатков по платежам: оплаченная часть и бонус отдельно (FIFO при расходе)."""

from __future__ import annotations

import logging
from decimal import Decimal

from app.db import pool

log = logging.getLogger("app.payment_buckets")

REFUND_WINDOW_DAYS = 14
_Q = Decimal("0.0001")
# Стабильный ключ для pg_advisory_lock (не пересекается с другими lock'ами в проекте).
_BACKFILL_LOCK = 88221401


def _d(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(_Q)


def init_paid_topup(topup_id: int, *, amount_usd: Decimal, bonus_usd: Decimal, decided_at=None) -> None:
    """Инициализирует корзины платежа после успешного зачисления."""
    amount = _d(amount_usd)
    bonus = _d(bonus_usd)
    with pool.connection() as conn:
        if decided_at is None:
            conn.execute(
                """
                UPDATE topups
                SET payment_remaining_usd = %s,
                    bonus_remaining_usd = %s,
                    refund_window_ends_at = COALESCE(decided_at, NOW()) + (%s * INTERVAL '1 day'),
                    buckets_initialized = TRUE
                WHERE id = %s AND status = 'paid'
                """,
                (amount, bonus, REFUND_WINDOW_DAYS, topup_id),
            )
        else:
            conn.execute(
                """
                UPDATE topups
                SET payment_remaining_usd = %s,
                    bonus_remaining_usd = %s,
                    refund_window_ends_at = %s + (%s * INTERVAL '1 day'),
                    buckets_initialized = TRUE
                WHERE id = %s AND status = 'paid'
                """,
                (amount, bonus, decided_at, REFUND_WINDOW_DAYS, topup_id),
            )


def apply_spend(user_id: int, spent: Decimal, conn=None) -> None:
    """Списывает расход FIFO: сначала оплаченная часть платежа, затем бонус."""
    remaining = _d(spent)
    if remaining <= 0:
        return

    def _run(c) -> None:
        nonlocal remaining
        rows = c.execute(
            """
            SELECT id, payment_remaining_usd, bonus_remaining_usd
            FROM topups
            WHERE user_id = %s
              AND status = 'paid'
              AND buckets_initialized
              AND (payment_remaining_usd > 0 OR bonus_remaining_usd > 0)
            ORDER BY decided_at ASC NULLS LAST, id ASC
            FOR UPDATE
            """,
            (user_id,),
        ).fetchall()
        for row in rows:
            if remaining <= 0:
                break
            pay = _d(row["payment_remaining_usd"])
            bon = _d(row["bonus_remaining_usd"])
            take_pay = min(pay, remaining)
            remaining = (remaining - take_pay).quantize(_Q)
            take_bon = min(bon, remaining)
            remaining = (remaining - take_bon).quantize(_Q)
            if take_pay == 0 and take_bon == 0:
                continue
            c.execute(
                """
                UPDATE topups
                SET payment_remaining_usd = %s,
                    bonus_remaining_usd = %s
                WHERE id = %s
                """,
                (pay - take_pay, bon - take_bon, int(row["id"])),
            )

    if conn is not None:
        _run(conn)
        return
    with pool.connection() as owned:
        _run(owned)


def backfill_uninitialized() -> int:
    """Инициализирует корзины у старых paid-платежей и распределяет исторический расход.

    Идемпотентно и под advisory-lock, чтобы два инстанса не списали spend дважды.
    """
    with pool.connection() as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_BACKFILL_LOCK,))
        try:
            pending = conn.execute(
                """
                SELECT DISTINCT user_id
                FROM topups
                WHERE status = 'paid' AND NOT buckets_initialized
                ORDER BY user_id
                """
            ).fetchall()
            if not pending:
                return 0

            total_topups = 0
            for row in pending:
                user_id = int(row["user_id"])
                still = conn.execute(
                    """
                    SELECT 1 FROM topups
                    WHERE user_id = %s AND status = 'paid' AND NOT buckets_initialized
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
                if still is None:
                    continue
                updated = conn.execute(
                    """
                    UPDATE topups
                    SET payment_remaining_usd = amount_usd,
                        bonus_remaining_usd = bonus_usd,
                        refund_window_ends_at = COALESCE(decided_at, NOW())
                            + (%s * INTERVAL '1 day'),
                        buckets_initialized = TRUE
                    WHERE user_id = %s AND status = 'paid'
                    RETURNING id
                    """,
                    (REFUND_WINDOW_DAYS, user_id),
                ).fetchall()
                total_topups += len(updated)
                spend_row = conn.execute(
                    """
                    SELECT COALESCE(SUM(amount_usd), 0) AS total
                    FROM ledger
                    WHERE user_id = %s AND kind = 'spend' AND amount_usd > 0
                    """,
                    (user_id,),
                ).fetchone()
                spent = _d(spend_row["total"] if spend_row else 0)
                if spent > 0:
                    apply_spend(user_id, spent, conn=conn)

            log.info("инициализированы корзины платежей: %s шт.", total_topups)
            return total_topups
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_BACKFILL_LOCK,))


def finance_bucket_totals() -> dict[str, Decimal]:
    """Агрегаты для финансов по платежам."""
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN refund_window_ends_at IS NOT NULL
                             AND refund_window_ends_at > NOW()
                        THEN payment_remaining_usd
                        ELSE 0
                    END
                ), 0) AS refund_liability_usd,
                COALESCE(SUM(
                    CASE
                        WHEN refund_window_ends_at IS NULL
                             OR refund_window_ends_at <= NOW()
                        THEN payment_remaining_usd
                        ELSE 0
                    END
                ), 0) AS settled_payment_usd,
                COALESCE(SUM(bonus_remaining_usd), 0) AS bonus_remaining_usd,
                COALESCE(SUM(bonus_usd), 0) AS bonus_granted_usd
            FROM topups
            WHERE status = 'paid' AND buckets_initialized
            """
        ).fetchone()
    return {
        "refund_liability_usd": _d(row["refund_liability_usd"]),
        "settled_payment_usd": _d(row["settled_payment_usd"]),
        "bonus_remaining_usd": _d(row["bonus_remaining_usd"]),
        "bonus_granted_usd": _d(row["bonus_granted_usd"]),
    }
