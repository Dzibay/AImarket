"""Компания: сводка и ручные проводки для страницы «Финансы»."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from app.db import pool
from app.money import units_to_usd, usd_price_rub
from app.settings_store import get_setting, set_setting
from app.upstream import UpstreamError, upstream

_MSK = ZoneInfo("Europe/Moscow")

KINDS = ("income", "expense", "reserve", "reserve_release", "withdrawal", "deposit")

KIND_LABELS = {
    "income": "Доход",
    "expense": "Расход",
    "reserve": "Резерв",
    "reserve_release": "Снятие резерва",
    "withdrawal": "Вывод",
    "deposit": "Взнос",
}

CATEGORIES = {
    "income": ("other", "refund_in", "correction", "partner"),
    "expense": (
        "yookassa_fee",
        "ads",
        "hosting",
        "domain",
        "tax",
        "salary",
        "tools",
        "legal",
        "other",
    ),
    "reserve": ("tax_reserve", "refund_reserve", "buffer", "other"),
    "reserve_release": ("tax_reserve", "refund_reserve", "buffer", "other"),
    "withdrawal": ("owner_payout", "transfer", "other"),
    "deposit": ("owner_in", "opening", "other"),
}

CATEGORY_LABELS = {
    "other": "Прочее",
    "refund_in": "Возврат нам",
    "correction": "Корректировка",
    "partner": "Партнёрский доход",
    "yookassa_fee": "Комиссия ЮKassa",
    "ads": "Реклама",
    "hosting": "Хостинг / сервер",
    "domain": "Домен",
    "tax": "Налоги",
    "salary": "Зарплата / подряд",
    "tools": "Сервисы / подписки",
    "legal": "Юр. / бух.",
    "tax_reserve": "Резерв под налоги",
    "refund_reserve": "Резерв под возвраты",
    "buffer": "Подушка",
    "owner_payout": "Вывод владельцу",
    "transfer": "Перевод со счёта",
    "owner_in": "Взнос владельца",
    "opening": "Ввод остатка",
}


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q4(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def opening_cash_rub() -> Decimal:
    raw = get_setting("finance_opening_cash_rub").strip().replace(",", ".")
    if not raw:
        return Decimal("0.00")
    try:
        return _q2(Decimal(raw))
    except Exception:
        return Decimal("0.00")


def set_opening_cash_rub(value: Decimal) -> Decimal:
    amount = _q2(value)
    set_setting("finance_opening_cash_rub", f"{amount:.2f}")
    return amount


def _manual_totals(conn) -> dict[str, Decimal]:
    rows = conn.execute(
        """
        SELECT kind,
               COALESCE(SUM(amount_rub), 0) AS rub,
               COALESCE(SUM(amount_usd), 0) AS usd
        FROM finance_entries
        GROUP BY kind
        """
    ).fetchall()
    out = {kind: {"rub": Decimal("0"), "usd": Decimal("0")} for kind in KINDS}
    for row in rows:
        kind = row["kind"]
        if kind in out:
            out[kind] = {"rub": _d(row["rub"]), "usd": _d(row["usd"])}
    return out


def _system_totals(conn) -> dict:
    paid = conn.execute(
        """
        SELECT
            COALESCE(SUM(amount_kopecks), 0) AS kop,
            COALESCE(SUM(amount_usd), 0) AS usd,
            COALESCE(SUM(bonus_usd), 0) AS bonus_usd,
            COUNT(*) AS count
        FROM topups
        WHERE status = 'paid'
        """
    ).fetchone()
    balances = conn.execute(
        "SELECT COALESCE(SUM(balance_usd), 0) AS total FROM users"
    ).fetchone()
    spend = conn.execute(
        "SELECT COALESCE(SUM(quota_units), 0) AS units FROM usage"
    ).fetchone()
    return {
        "topups_rub": _q2(_d(paid["kop"]) / Decimal(100)),
        "topups_usd": _q4(_d(paid["usd"])),
        "bonuses_usd": _q4(_d(paid["bonus_usd"])),
        "topups_count": int(paid["count"] or 0),
        "customer_liability_usd": _q4(_d(balances["total"])),
        "usage_spend_usd": _q4(units_to_usd(int(spend["units"] or 0))),
    }


def build_summary() -> dict:
    rate = usd_price_rub()
    with pool.connection() as conn:
        system = _system_totals(conn)
        manual = _manual_totals(conn)
        recent = conn.execute(
            """
            SELECT id, kind, category, amount_rub, amount_usd, note, occurred_at, created_at
            FROM finance_entries
            ORDER BY occurred_at DESC, id DESC
            LIMIT 200
            """
        ).fetchall()

    supplier = Decimal("0")
    try:
        supplier = _q4(_d(upstream.supplier_balance_usd()))
    except UpstreamError:
        supplier = Decimal("0")

    opening = opening_cash_rub()
    income_m = manual["income"]["rub"]
    expense_m = manual["expense"]["rub"]
    withdrawal_m = manual["withdrawal"]["rub"]
    deposit_m = manual["deposit"]["rub"]
    reserves_net = manual["reserve"]["rub"] - manual["reserve_release"]["rub"]
    if reserves_net < 0:
        reserves_net = Decimal("0")

    topups_rub = system["topups_rub"]
    customer_usd = system["customer_liability_usd"]
    customer_rub = _q2(customer_usd * rate) if rate > 0 else Decimal("0")

    cash_book = _q2(opening + topups_rub + income_m + deposit_m - expense_m - withdrawal_m)
    obligations = _q2(customer_rub + reserves_net)
    available = _q2(cash_book - obligations)

    # Прибыльность по модели: оплаты клиентов минус расход квот и бонусы.
    gross_usd = _q4(system["topups_usd"] - system["usage_spend_usd"] - system["bonuses_usd"])

    return {
        "rate": float(rate),
        "opening_cash_rub": float(opening),
        "cash_book_rub": float(cash_book),
        "available_rub": float(available),
        "available_usd": float(_q4(available / rate)) if rate > 0 else 0.0,
        "obligations_rub": float(obligations),
        "reserves_net_rub": float(_q2(reserves_net)),
        "customer_liability_usd": float(customer_usd),
        "customer_liability_rub": float(customer_rub),
        "supplier_balance_usd": float(supplier),
        "topups": {
            "count": system["topups_count"],
            "rub": float(topups_rub),
            "usd": float(system["topups_usd"]),
            "bonus_usd": float(system["bonuses_usd"]),
        },
        "usage_spend_usd": float(system["usage_spend_usd"]),
        "gross_margin_usd": float(gross_usd),
        "manual": {
            kind: {"rub": float(vals["rub"]), "usd": float(vals["usd"])}
            for kind, vals in manual.items()
        },
        "breakdown": [
            {"label": "Стартовый остаток кассы", "rub": float(opening), "sign": "+"},
            {"label": "Оплаты ЮKassa (paid)", "rub": float(topups_rub), "sign": "+"},
            {"label": "Прочие доходы", "rub": float(_q2(income_m)), "sign": "+"},
            {"label": "Взносы в кассу", "rub": float(_q2(deposit_m)), "sign": "+"},
            {"label": "Расходы", "rub": float(_q2(expense_m)), "sign": "−"},
            {"label": "Выводы", "rub": float(_q2(withdrawal_m)), "sign": "−"},
            {"label": "Касса (книга)", "rub": float(cash_book), "sign": "=", "emphasis": True},
            {"label": "Обязательства клиентам", "rub": float(customer_rub), "sign": "−"},
            {"label": "Резервы", "rub": float(_q2(reserves_net)), "sign": "−"},
            {
                "label": "Доступно к выводу",
                "rub": float(available),
                "sign": "=",
                "emphasis": True,
                "tone": "ok" if available >= 0 else "bad",
            },
        ],
        "meta": {
            "kinds": [{"value": k, "label": KIND_LABELS[k]} for k in KINDS],
            "categories": {
                kind: [{"value": c, "label": CATEGORY_LABELS.get(c, c)} for c in cats]
                for kind, cats in CATEGORIES.items()
            },
        },
        "entries": [_entry_row(row) for row in recent],
    }


def _entry_row(row) -> dict:
    kind = row["kind"]
    category = row["category"] or "other"
    return {
        "id": row["id"],
        "kind": kind,
        "kind_label": KIND_LABELS.get(kind, kind),
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "amount_rub": float(_d(row["amount_rub"])),
        "amount_usd": float(_d(row["amount_usd"])),
        "note": row["note"] or "",
        "occurred_at": row["occurred_at"].isoformat() if row["occurred_at"] else "",
        "created_at": row["created_at"].isoformat() if row["created_at"] else "",
    }


def list_entries(kind: str | None = None, limit: int = 200) -> list[dict]:
    limit = max(1, min(int(limit), 500))
    with pool.connection() as conn:
        if kind and kind in KINDS:
            rows = conn.execute(
                """
                SELECT id, kind, category, amount_rub, amount_usd, note, occurred_at, created_at
                FROM finance_entries
                WHERE kind = %s
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
                (kind, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, kind, category, amount_rub, amount_usd, note, occurred_at, created_at
                FROM finance_entries
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
    return [_entry_row(row) for row in rows]


def create_entry(
    *,
    kind: str,
    category: str,
    amount_rub: Decimal,
    amount_usd: Decimal = Decimal("0"),
    note: str = "",
    occurred_at: datetime | None = None,
) -> dict:
    if kind not in KINDS:
        raise ValueError("kind")
    amount_rub = _q2(amount_rub)
    amount_usd = _q4(amount_usd)
    if amount_rub <= 0:
        raise ValueError("amount")
    allowed = CATEGORIES.get(kind, ("other",))
    cat = (category or "other").strip() or "other"
    if cat not in allowed:
        cat = "other"
    when = occurred_at or datetime.now(_MSK)
    with pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO finance_entries (kind, category, amount_rub, amount_usd, note, occurred_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, kind, category, amount_rub, amount_usd, note, occurred_at, created_at
            """,
            (kind, cat, amount_rub, amount_usd, note.strip()[:500], when),
        ).fetchone()
    return _entry_row(row)


def delete_entry(entry_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            "DELETE FROM finance_entries WHERE id = %s RETURNING id",
            (entry_id,),
        ).fetchone()
    return row is not None
