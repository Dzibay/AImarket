"""Зачислить все оплаченные, но не зачисленные topups. Запуск в контейнере backend."""
import sys

sys.path.insert(0, "/app")

from app.db import ensure_schema, pool
from app.payments import settle_payment

try:
    from app.payments import recover_paid_topup
except ImportError:
    recover_paid_topup = None


def main() -> None:
    ensure_schema()

    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.user_id, t.status, t.payment_id, t.amount_usd, t.bonus_usd, u.email
            FROM topups t
            JOIN users u ON u.id = t.user_id
            WHERE t.status IN ('pending', 'awaiting_supplier') AND t.payment_id IS NOT NULL
            ORDER BY t.id
            """
        ).fetchall()

    print(f"Found {len(rows)} uncredited topups")
    for row in rows:
        tid = int(row["id"])
        pid = str(row["payment_id"])
        uid = int(row["user_id"])
        email = row["email"] or "-"
        print(
            f"--- topup #{tid} user={uid} status={row['status']} "
            f"email={email} usd={row['amount_usd']}+{row['bonus_usd'] or 0}"
        )
        try:
            result = settle_payment(pid)
            print(f"  -> {result}")
        except Exception as exc:
            print(f"  settle failed: {exc}")
            if recover_paid_topup is not None:
                try:
                    result = recover_paid_topup(tid, pid, uid)
                    print(f"  recover -> {result}")
                except Exception as exc2:
                    print(f"  recover failed: {exc2}")

    with pool.connection() as conn:
        left = conn.execute(
            """
            SELECT id, status, user_id FROM topups
            WHERE status IN ('pending', 'awaiting_supplier') AND payment_id IS NOT NULL
            ORDER BY id
            """
        ).fetchall()
    print(f"Remaining: {len(left)}")
    for r in left:
        print(f"  #{r['id']} user={r['user_id']} {r['status']}")


if __name__ == "__main__":
    main()
