import sys

sys.path.insert(0, "/app")

from app.db import ensure_schema, pool
from app.yookassa import get_payment, YooKassaError


def main() -> None:
    ensure_schema()
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.user_id, t.status, t.payment_id, t.amount_usd, u.email
            FROM topups t
            JOIN users u ON u.id = t.user_id
            WHERE t.status IN ('pending', 'awaiting_supplier') AND t.payment_id IS NOT NULL
            ORDER BY t.id
            """
        ).fetchall()
    for row in rows:
        pid = str(row["payment_id"])
        try:
            p = get_payment(pid)
            st = p.get("status")
            paid = bool(p.get("paid"))
        except YooKassaError as exc:
            st = f"error: {exc.message}"
            paid = False
        print(
            f"#{row['id']} user={row['user_id']} db={row['status']} "
            f"yookassa={st} paid={paid} email={row['email'] or '-'}"
        )


if __name__ == "__main__":
    main()
