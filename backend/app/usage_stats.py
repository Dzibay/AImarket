"""Агрегаты расходов из таблицы usage — один источник для профиля и экрана ключа."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.money import units_to_usd
from app.msk_dates import _MSK_DAY, _MSK_MONTH, _MSK_TODAY

MSK = ZoneInfo("Europe/Moscow")
WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def week_start_msk() -> date:
    return datetime.now(MSK).date() - timedelta(days=6)


def today_msk() -> date:
    return datetime.now(MSK).date()


def week_chart(by_day: dict[date, float]) -> list[dict]:
    start = week_start_msk()
    today = today_msk()
    return [
        {
            "date": day.isoformat(),
            "label": f"{day.strftime('%d.%m')} {WEEKDAY_LABELS[day.weekday()]}",
            "is_today": day == today,
            "usd": by_day.get(day, 0.0),
        }
        for day in (start + timedelta(days=offset) for offset in range(7))
    ]


def usage_period_stats(conn, user_id: int) -> dict:
    """Суммы и график за сегодня / месяц / 7 дней по user_id."""
    start = week_start_msk()
    row = conn.execute(
        f"""
        SELECT
            COALESCE(SUM(quota_units) FILTER (WHERE {_MSK_TODAY}), 0) AS today_units,
            COALESCE(SUM(quota_units) FILTER (WHERE {_MSK_MONTH}), 0) AS month_units,
            COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
            COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
            COALESCE(SUM(quota_units), 0) AS spent_units,
            MAX(created_at) AS last_request_at
        FROM usage
        WHERE user_id = %s
        """,
        (user_id,),
    ).fetchone()
    week_rows = conn.execute(
        f"""
        SELECT {_MSK_DAY} AS day, COALESCE(SUM(quota_units), 0) AS units
        FROM usage
        WHERE user_id = %s AND {_MSK_DAY} >= %s
        GROUP BY day
        ORDER BY day
        """,
        (user_id, start),
    ).fetchall()
    by_day = {r["day"]: float(units_to_usd(int(r["units"] or 0))) for r in week_rows}
    today = today_msk()
    return {
        "spent_today_usd": float(units_to_usd(int(row["today_units"] or 0))),
        "spent_month_usd": float(units_to_usd(int(row["month_units"] or 0))),
        "spent_week_usd": week_chart(by_day),
        "spent_today_date": today.isoformat(),
        "prompt_tokens": int(row["prompt_tokens"] or 0),
        "completion_tokens": int(row["completion_tokens"] or 0),
        "spent_units": int(row["spent_units"] or 0),
        "last_request_at": row["last_request_at"],
    }
