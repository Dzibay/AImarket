"""История операций пользователя: пополнения из журнала и расходы из usage. Общая для бота и сайта."""

from app.datetime_util import iso_utc
from app.db import pool
from app.money import units_to_usd

HISTORY_PAGE = 5

_HISTORY_KINDS = {
    "topup": "Пополнение",
    "credit": "Начисление",
    "spend": "Расход",
    "adjust": "Сверка",
}


def history_filter(raw: str) -> str:
    value = (raw or "all").strip().lower()
    if value in {"income", "in", "topup", "topups"}:
        return "income"
    if value in {"spend", "out", "spends"}:
        return "spend"
    return "all"


def _history_item(row: dict) -> dict:
    entry_type = str(row["entry_type"])
    kind = str(row["kind"])
    if entry_type == "income":
        return {
            "entry_type": "income",
            "kind": kind,
            "label": _HISTORY_KINDS.get(kind, kind),
            "note": row["note"] or "",
            "amount_usd": float(row["amount_usd"]),
            "amount_rub": float(int(row["amount_kopecks"] or 0)) / 100,
            "created_at": iso_utc(row["created_at"]),
        }
    if entry_type == "ledger_spend":
        note = str(row["note"] or "").strip()
        return {
            "entry_type": "spend",
            "kind": kind,
            "label": _HISTORY_KINDS.get(kind, kind),
            "model": note or "Расход API",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "amount_usd": float(row["amount_usd"]),
            "created_at": iso_utc(row["created_at"]),
        }
    return {
        "entry_type": "spend",
        "kind": "spend",
        "label": "Расход",
        "model": str(row["model_name"] or "—"),
        "prompt_tokens": int(row["prompt_tokens"] or 0),
        "completion_tokens": int(row["completion_tokens"] or 0),
        "amount_usd": float(units_to_usd(int(row["quota_units"] or 0))),
        "created_at": iso_utc(row["created_at"]),
    }


def _user_has_spend_history(conn, user_id: int) -> bool:
    usage = conn.execute("SELECT 1 FROM usage WHERE user_id = %s LIMIT 1", (user_id,)).fetchone()
    if usage is not None:
        return True
    ledger = conn.execute(
        "SELECT 1 FROM ledger WHERE user_id = %s AND kind IN ('spend', 'adjust') LIMIT 1",
        (user_id,),
    ).fetchone()
    return ledger is not None


def history_payload(user_id: int, filter: str = "all", offset: int = 0, limit: int = HISTORY_PAGE) -> dict:
    kind = history_filter(filter)
    offset = max(0, offset)
    limit = min(max(1, limit), 30)
    with pool.connection() as conn:
        usage_count = int(
            conn.execute("SELECT COUNT(*) AS c FROM usage WHERE user_id = %s", (user_id,)).fetchone()["c"]
        )
        parts: list[str] = []
        params: list[object] = []
        if kind in {"all", "income"}:
            parts.append(
                """
                SELECT 'income' AS entry_type, kind, note, amount_usd, amount_kopecks,
                       NULL::text AS model_name, NULL::int AS prompt_tokens,
                       NULL::int AS completion_tokens, NULL::bigint AS quota_units, created_at
                FROM ledger
                WHERE user_id = %s AND kind IN ('topup', 'credit')
                """
            )
            params.append(user_id)
        if kind in {"all", "spend"}:
            if usage_count > 0:
                parts.append(
                    """
                    SELECT 'spend' AS entry_type, 'spend' AS kind, '' AS note,
                           0::numeric AS amount_usd, 0 AS amount_kopecks,
                           model_name, prompt_tokens, completion_tokens, quota_units, created_at
                    FROM usage
                    WHERE user_id = %s
                    """
                )
                params.append(user_id)
            else:
                parts.append(
                    """
                    SELECT 'ledger_spend' AS entry_type, kind, note, amount_usd, amount_kopecks,
                           NULL::text AS model_name, NULL::int AS prompt_tokens,
                           NULL::int AS completion_tokens, NULL::bigint AS quota_units, created_at
                    FROM ledger
                    WHERE user_id = %s AND kind = 'spend'
                    """
                )
                params.append(user_id)
        if kind == "all" and usage_count == 0:
            parts.append(
                """
                SELECT 'ledger_spend' AS entry_type, kind, note, amount_usd, amount_kopecks,
                       NULL::text AS model_name, NULL::int AS prompt_tokens,
                       NULL::int AS completion_tokens, NULL::bigint AS quota_units, created_at
                FROM ledger
                WHERE user_id = %s AND kind = 'adjust'
                """
            )
            params.append(user_id)
        if not parts:
            return {"items": [], "offset": offset, "limit": limit, "has_more": False, "filter": kind, "has_any": False}
        query = f"""
            SELECT * FROM (
                {" UNION ALL ".join(parts)}
            ) history
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit + 1, offset])
        rows = conn.execute(query, tuple(params)).fetchall()
        has_any = True
        if offset == 0 and not rows:
            income = conn.execute(
                """
                SELECT 1 FROM ledger
                WHERE user_id = %s AND kind IN ('topup', 'credit')
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            has_any = income is not None or _user_has_spend_history(conn, user_id)
    has_more = len(rows) > limit
    return {
        "items": [_history_item(row) for row in rows[:limit]],
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "filter": kind,
        "has_any": has_any,
    }
