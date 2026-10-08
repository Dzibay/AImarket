"""Бухгалтерия компании: счета, категории, расходы, выводы, операции."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from app.db import pool
from app.money import supplier_usd_price_rub, usd_price_rub
from app.upstream import UpstreamError, upstream

_MSK = ZoneInfo("Europe/Moscow")

OP_KINDS = ("income", "expense", "withdrawal", "deposit", "transfer")
CAT_KINDS = ("expense", "withdrawal")
PROVIDERS = {
    "yookassa": "ЮKassa",
}

KIND_LABELS = {
    "income": "Приход",
    "expense": "Расход",
    "withdrawal": "Вывод",
    "deposit": "Пополнение счёта",
    "transfer": "Перевод",
}


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q4(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(_MSK)


def _parse_when(raw: str | None) -> datetime:
    if not raw or not str(raw).strip():
        return _now()
    value = str(raw).strip()
    try:
        if len(value) == 10 and value[4] == "-" and value[7] == "-":
            return datetime.combine(date.fromisoformat(value), datetime.min.time(), tzinfo=_MSK)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("occurred_at") from exc


def _norm_color(color: str) -> str:
    value = (color or "").strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value.lower()
        except ValueError:
            pass
    return "#6b645b"


# --- categories -----------------------------------------------------------------


def list_categories(kind: str | None = None, *, include_archived: bool = False) -> list[dict]:
    clauses = []
    params: list = []
    if kind in CAT_KINDS:
        clauses.append("kind = %s")
        params.append(kind)
    if not include_archived:
        clauses.append("archived_at IS NULL")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, name, color, kind, sort_order, archived_at, created_at
            FROM finance_categories
            {where}
            ORDER BY sort_order, id
            """,
            params,
        ).fetchall()
    return [_category_row(row) for row in rows]


def create_category(*, name: str, color: str, kind: str, sort_order: int = 100) -> dict:
    if kind not in CAT_KINDS:
        raise ValueError("kind")
    title = name.strip()
    if not title:
        raise ValueError("name")
    with pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO finance_categories (name, color, kind, sort_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, color, kind, sort_order, archived_at, created_at
            """,
            (title[:80], _norm_color(color), kind, int(sort_order)),
        ).fetchone()
    return _category_row(row)


def update_category(category_id: int, *, name: str, color: str, sort_order: int | None = None) -> dict:
    title = name.strip()
    if not title:
        raise ValueError("name")
    with pool.connection() as conn:
        if sort_order is None:
            row = conn.execute(
                """
                UPDATE finance_categories
                SET name = %s, color = %s
                WHERE id = %s
                RETURNING id, name, color, kind, sort_order, archived_at, created_at
                """,
                (title[:80], _norm_color(color), category_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                UPDATE finance_categories
                SET name = %s, color = %s, sort_order = %s
                WHERE id = %s
                RETURNING id, name, color, kind, sort_order, archived_at, created_at
                """,
                (title[:80], _norm_color(color), int(sort_order), category_id),
            ).fetchone()
    if row is None:
        raise LookupError("category")
    return _category_row(row)


def archive_category(category_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            """
            UPDATE finance_categories
            SET archived_at = COALESCE(archived_at, NOW())
            WHERE id = %s
            RETURNING id
            """,
            (category_id,),
        ).fetchone()
    return row is not None


def _category_row(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "color": row["color"],
        "kind": row["kind"],
        "sort_order": int(row["sort_order"] or 0),
        "archived": row["archived_at"] is not None,
    }


# --- accounts -------------------------------------------------------------------


def list_accounts() -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.name, a.provider_key, a.is_default, a.note, a.created_at,
                   COALESCE((
                       SELECT SUM(
                           CASE
                               WHEN o.kind IN ('income', 'deposit') THEN o.amount_rub
                               WHEN o.kind IN ('expense', 'withdrawal') THEN -o.amount_rub
                               WHEN o.kind = 'transfer' THEN -o.amount_rub
                               ELSE 0
                           END
                       )
                       FROM finance_operations o
                       WHERE o.account_id = a.id
                   ), 0)
                   + COALESCE((
                       SELECT SUM(t.amount_rub)
                       FROM finance_operations t
                       WHERE t.kind = 'transfer' AND t.counterparty_account_id = a.id
                   ), 0) AS balance_rub
            FROM finance_accounts a
            ORDER BY a.is_default DESC, a.id
            """
        ).fetchall()
    return [_account_row(row) for row in rows]


def create_account(
    *,
    name: str,
    provider_key: str = "",
    is_default: bool = False,
    note: str = "",
    import_history: bool = True,
) -> dict:
    title = name.strip()
    if not title:
        raise ValueError("name")
    key = (provider_key or "").strip().lower()
    if key and key not in PROVIDERS:
        raise ValueError("provider")
    with pool.connection() as conn:
        if key:
            exists = conn.execute(
                "SELECT id FROM finance_accounts WHERE provider_key = %s",
                (key,),
            ).fetchone()
            if exists:
                raise ValueError("provider_exists")
        if is_default:
            conn.execute("UPDATE finance_accounts SET is_default = FALSE WHERE is_default")
        row = conn.execute(
            """
            INSERT INTO finance_accounts (name, provider_key, is_default, note)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, provider_key, is_default, note, created_at
            """,
            (title[:120], key, bool(is_default), note.strip()[:300]),
        ).fetchone()
        account_id = int(row["id"])
        imported = 0
        if key == "yookassa" and import_history:
            imported = _import_yookassa_history(conn, account_id)
    out = _account_row({**row, "balance_rub": Decimal("0")})
    out["imported"] = imported
    # refresh balance
    accounts = {a["id"]: a for a in list_accounts()}
    return accounts.get(account_id, out)


def update_account(
    account_id: int,
    *,
    name: str,
    is_default: bool | None = None,
    note: str | None = None,
) -> dict:
    title = name.strip()
    if not title:
        raise ValueError("name")
    with pool.connection() as conn:
        current = conn.execute(
            "SELECT id, provider_key FROM finance_accounts WHERE id = %s",
            (account_id,),
        ).fetchone()
        if current is None:
            raise LookupError("account")
        if is_default:
            conn.execute("UPDATE finance_accounts SET is_default = FALSE WHERE is_default")
        sets = ["name = %s"]
        params: list = [title[:120]]
        if is_default is not None:
            sets.append("is_default = %s")
            params.append(bool(is_default))
        if note is not None:
            sets.append("note = %s")
            params.append(note.strip()[:300])
        params.append(account_id)
        row = conn.execute(
            f"""
            UPDATE finance_accounts
            SET {", ".join(sets)}
            WHERE id = %s
            RETURNING id, name, provider_key, is_default, note, created_at
            """,
            params,
        ).fetchone()
    accounts = {a["id"]: a for a in list_accounts()}
    return accounts.get(int(row["id"]), _account_row({**row, "balance_rub": 0}))


def delete_account(account_id: int) -> bool:
    with pool.connection() as conn:
        used = conn.execute(
            """
            SELECT 1 FROM finance_operations
            WHERE account_id = %s OR counterparty_account_id = %s
            LIMIT 1
            """,
            (account_id, account_id),
        ).fetchone()
        if used:
            raise ValueError("in_use")
        row = conn.execute(
            "DELETE FROM finance_accounts WHERE id = %s RETURNING id",
            (account_id,),
        ).fetchone()
    return row is not None


def default_account_id() -> int | None:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id FROM finance_accounts WHERE is_default ORDER BY id LIMIT 1"
        ).fetchone()
        if row:
            return int(row["id"])
        row = conn.execute("SELECT id FROM finance_accounts ORDER BY id LIMIT 1").fetchone()
        return int(row["id"]) if row else None


def provider_account_id(provider_key: str) -> int | None:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id FROM finance_accounts WHERE provider_key = %s",
            (provider_key,),
        ).fetchone()
    return int(row["id"]) if row else None


def _account_row(row) -> dict:
    key = row["provider_key"] or ""
    return {
        "id": row["id"],
        "name": row["name"],
        "provider_key": key,
        "provider_label": PROVIDERS.get(key, ""),
        "is_default": bool(row["is_default"]),
        "note": row.get("note") or "",
        "balance_rub": float(_q2(_d(row.get("balance_rub")))),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
    }


def _import_yookassa_history(conn, account_id: int) -> int:
    rows = conn.execute(
        """
        SELECT id, amount_kopecks, amount_usd, payment_id, decided_at, created_at
        FROM topups
        WHERE status = 'paid'
        ORDER BY id
        """
    ).fetchall()
    imported = 0
    for row in rows:
        ref = f"topup:{row['id']}"
        exists = conn.execute(
            """
            SELECT 1 FROM finance_operations
            WHERE source = 'yookassa' AND source_ref = %s
            """,
            (ref,),
        ).fetchone()
        if exists:
            continue
        when = row["decided_at"] or row["created_at"] or _now()
        note = f"ЮKassa {row['payment_id']}" if row["payment_id"] else f"Оплата #{row['id']}"
        conn.execute(
            """
            INSERT INTO finance_operations
                (kind, account_id, amount_rub, amount_usd, note, occurred_at, source, source_ref)
            VALUES ('income', %s, %s, %s, %s, %s, 'yookassa', %s)
            """,
            (
                account_id,
                _q2(_d(row["amount_kopecks"]) / Decimal(100)),
                _q4(_d(row["amount_usd"])),
                note[:300],
                when,
                ref,
            ),
        )
        imported += 1
    return imported


def record_yookassa_payment(
    *,
    topup_id: int,
    amount_kopecks: int,
    amount_usd: Decimal,
    payment_id: str,
    occurred_at: datetime | None = None,
) -> None:
    account_id = provider_account_id("yookassa")
    if account_id is None:
        return
    ref = f"topup:{topup_id}"
    note = f"ЮKassa {payment_id}" if payment_id else f"Оплата #{topup_id}"
    with pool.connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM finance_operations WHERE source = 'yookassa' AND source_ref = %s",
            (ref,),
        ).fetchone()
        if exists:
            return
        conn.execute(
            """
            INSERT INTO finance_operations
                (kind, account_id, amount_rub, amount_usd, note, occurred_at, source, source_ref)
            VALUES ('income', %s, %s, %s, %s, %s, 'yookassa', %s)
            """,
            (
                account_id,
                _q2(_d(amount_kopecks) / Decimal(100)),
                _q4(_d(amount_usd)),
                note[:300],
                occurred_at or _now(),
                ref,
            ),
        )


# --- operations -----------------------------------------------------------------


def list_operations(kind: str | None = None, limit: int = 300) -> list[dict]:
    limit = max(1, min(int(limit), 500))
    params: list = []
    where = ""
    if kind in OP_KINDS:
        where = "WHERE o.kind = %s"
        params.append(kind)
    params.append(limit)
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT o.id, o.kind, o.account_id, o.counterparty_account_id, o.category_id,
                   o.amount_rub, o.amount_usd, o.note, o.occurred_at, o.source, o.source_ref,
                   o.created_at, o.updated_at,
                   a.name AS account_name,
                   ca.name AS counterparty_name,
                   c.name AS category_name, c.color AS category_color
            FROM finance_operations o
            JOIN finance_accounts a ON a.id = o.account_id
            LEFT JOIN finance_accounts ca ON ca.id = o.counterparty_account_id
            LEFT JOIN finance_categories c ON c.id = o.category_id
            {where}
            ORDER BY o.occurred_at DESC, o.id DESC
            LIMIT %s
            """,
            params,
        ).fetchall()
    return [_operation_row(row) for row in rows]


def create_operation(
    *,
    kind: str,
    account_id: int,
    amount_rub: Decimal,
    amount_usd: Decimal = Decimal("0"),
    category_id: int | None = None,
    counterparty_account_id: int | None = None,
    note: str = "",
    occurred_at: datetime | None = None,
) -> dict:
    if kind not in OP_KINDS:
        raise ValueError("kind")
    amount_rub = _q2(amount_rub)
    amount_usd = _q4(amount_usd)
    if amount_rub <= 0:
        raise ValueError("amount")
    if kind == "transfer":
        if not counterparty_account_id or int(counterparty_account_id) == int(account_id):
            raise ValueError("counterparty")
    else:
        counterparty_account_id = None
    if kind in ("expense", "withdrawal") and category_id:
        _require_category(category_id, kind)
    elif kind not in ("expense", "withdrawal"):
        category_id = None
    when = occurred_at or _now()
    with pool.connection() as conn:
        _require_account(conn, account_id)
        if counterparty_account_id:
            _require_account(conn, counterparty_account_id)
        row = conn.execute(
            """
            INSERT INTO finance_operations
                (kind, account_id, counterparty_account_id, category_id,
                 amount_rub, amount_usd, note, occurred_at, source, source_ref)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'manual', '')
            RETURNING id
            """,
            (
                kind,
                account_id,
                counterparty_account_id,
                category_id,
                amount_rub,
                amount_usd,
                note.strip()[:500],
                when,
            ),
        ).fetchone()
    return get_operation(int(row["id"]))


def update_operation(
    operation_id: int,
    *,
    account_id: int | None = None,
    category_id: int | None = None,
    amount_rub: Decimal | None = None,
    amount_usd: Decimal | None = None,
    note: str | None = None,
    occurred_at: datetime | None = None,
    clear_category: bool = False,
) -> dict:
    with pool.connection() as conn:
        current = conn.execute(
            "SELECT * FROM finance_operations WHERE id = %s",
            (operation_id,),
        ).fetchone()
        if current is None:
            raise LookupError("operation")
        if current["source"] != "manual":
            raise ValueError("locked")
        kind = current["kind"]
        new_account = account_id if account_id is not None else int(current["account_id"])
        _require_account(conn, new_account)
        new_amount = _q2(amount_rub) if amount_rub is not None else _d(current["amount_rub"])
        if new_amount <= 0:
            raise ValueError("amount")
        new_usd = _q4(amount_usd) if amount_usd is not None else _d(current["amount_usd"])
        if clear_category:
            new_cat = None
        elif category_id is not None:
            new_cat = category_id
            if kind in ("expense", "withdrawal"):
                _require_category(new_cat, kind)
        else:
            new_cat = current["category_id"]
        new_note = note.strip()[:500] if note is not None else (current["note"] or "")
        new_when = occurred_at if occurred_at is not None else current["occurred_at"]
        conn.execute(
            """
            UPDATE finance_operations
            SET account_id = %s,
                category_id = %s,
                amount_rub = %s,
                amount_usd = %s,
                note = %s,
                occurred_at = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (new_account, new_cat, new_amount, new_usd, new_note, new_when, operation_id),
        )
    return get_operation(operation_id)


def delete_operation(operation_id: int) -> bool:
    with pool.connection() as conn:
        current = conn.execute(
            "SELECT source FROM finance_operations WHERE id = %s",
            (operation_id,),
        ).fetchone()
        if current is None:
            return False
        if current["source"] != "manual":
            raise ValueError("locked")
        conn.execute("DELETE FROM finance_operations WHERE id = %s", (operation_id,))
    return True


def get_operation(operation_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT o.id, o.kind, o.account_id, o.counterparty_account_id, o.category_id,
                   o.amount_rub, o.amount_usd, o.note, o.occurred_at, o.source, o.source_ref,
                   o.created_at, o.updated_at,
                   a.name AS account_name,
                   ca.name AS counterparty_name,
                   c.name AS category_name, c.color AS category_color
            FROM finance_operations o
            JOIN finance_accounts a ON a.id = o.account_id
            LEFT JOIN finance_accounts ca ON ca.id = o.counterparty_account_id
            LEFT JOIN finance_categories c ON c.id = o.category_id
            WHERE o.id = %s
            """,
            (operation_id,),
        ).fetchone()
    if row is None:
        raise LookupError("operation")
    return _operation_row(row)


def _require_account(conn, account_id: int) -> None:
    row = conn.execute("SELECT id FROM finance_accounts WHERE id = %s", (account_id,)).fetchone()
    if row is None:
        raise ValueError("account")


def _require_category(category_id: int, kind: str) -> None:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT id FROM finance_categories
            WHERE id = %s AND kind = %s AND archived_at IS NULL
            """,
            (category_id, kind),
        ).fetchone()
    if row is None:
        raise ValueError("category")


def _operation_row(row) -> dict:
    kind = row["kind"]
    return {
        "id": row["id"],
        "kind": kind,
        "kind_label": KIND_LABELS.get(kind, kind),
        "account_id": row["account_id"],
        "account_name": row["account_name"],
        "counterparty_account_id": row["counterparty_account_id"],
        "counterparty_name": row.get("counterparty_name") or "",
        "category_id": row["category_id"],
        "category_name": row.get("category_name") or "",
        "category_color": row.get("category_color") or "",
        "amount_rub": float(_d(row["amount_rub"])),
        "amount_usd": float(_d(row["amount_usd"])),
        "note": row["note"] or "",
        "occurred_at": row["occurred_at"].isoformat() if row["occurred_at"] else "",
        "source": row["source"],
        "source_ref": row["source_ref"] or "",
        "locked": row["source"] != "manual",
        "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else "",
    }


# --- summary --------------------------------------------------------------------


def build_summary() -> dict:
    customer_rate = usd_price_rub()
    supplier_rate = supplier_usd_price_rub()
    accounts = list_accounts()
    categories = list_categories()
    expenses = list_operations("expense", limit=200)
    withdrawals = list_operations("withdrawal", limit=200)
    operations = list_operations(limit=200)

    with pool.connection() as conn:
        balances = conn.execute(
            "SELECT COALESCE(SUM(balance_usd), 0) AS total FROM users"
        ).fetchone()
        paid = conn.execute(
            """
            SELECT COALESCE(SUM(amount_kopecks), 0) AS kop,
                   COALESCE(SUM(amount_usd), 0) AS usd,
                   COUNT(*) AS count
            FROM topups WHERE status = 'paid'
            """
        ).fetchone()

    customer_liability_usd = _q4(_d(balances["total"]))
    customer_liability_rub = _q2(customer_liability_usd * customer_rate) if customer_rate > 0 else Decimal("0")

    supplier = Decimal("0")
    supplier_error = ""
    try:
        supplier = _q4(_d(upstream.supplier_balance_usd()))
    except UpstreamError as exc:
        supplier_error = exc.message

    shortfall_usd = _q4(max(Decimal("0"), customer_liability_usd - supplier))
    shortfall_rub = _q2(shortfall_usd * supplier_rate) if supplier_rate > 0 else Decimal("0")

    cash_rub = _q2(sum((_d(a["balance_rub"]) for a in accounts), Decimal("0")))
    available_rub = _q2(cash_rub - customer_liability_rub)

    expenses_rub = _q2(sum((_d(x["amount_rub"]) for x in expenses), Decimal("0")))
    withdrawals_rub = _q2(sum((_d(x["amount_rub"]) for x in withdrawals), Decimal("0")))

    return {
        "customer_rate": float(customer_rate),
        "supplier_rate": float(supplier_rate),
        "cash_rub": float(cash_rub),
        "available_rub": float(available_rub),
        "available_usd": float(_q4(available_rub / customer_rate)) if customer_rate > 0 else 0.0,
        "customer_liability_usd": float(customer_liability_usd),
        "customer_liability_rub": float(customer_liability_rub),
        "supplier_balance_usd": float(supplier),
        "supplier_error": supplier_error,
        "supplier_shortfall_usd": float(shortfall_usd),
        "supplier_shortfall_rub": float(shortfall_rub),
        "supplier_needs_topup": shortfall_usd > 0,
        "expenses_total_rub": float(expenses_rub),
        "withdrawals_total_rub": float(withdrawals_rub),
        "topups": {
            "count": int(paid["count"] or 0),
            "rub": float(_q2(_d(paid["kop"]) / Decimal(100))),
            "usd": float(_q4(_d(paid["usd"]))),
        },
        "providers": [{"value": k, "label": v} for k, v in PROVIDERS.items()],
        "accounts": accounts,
        "categories": categories,
        "expenses": expenses,
        "withdrawals": withdrawals,
        "operations": operations,
        "default_account_id": default_account_id(),
    }
