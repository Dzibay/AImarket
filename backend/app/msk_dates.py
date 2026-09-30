"""Фильтры дат по календарю Europe/Moscow — одинаково для истории и статистики."""

_MSK_TODAY = "(created_at AT TIME ZONE 'Europe/Moscow')::date = (NOW() AT TIME ZONE 'Europe/Moscow')::date"
_MSK_MONTH = (
    "(created_at AT TIME ZONE 'Europe/Moscow')::date >= "
    "date_trunc('month', NOW() AT TIME ZONE 'Europe/Moscow')::date"
)
_MSK_DAY = "(created_at AT TIME ZONE 'Europe/Moscow')::date"
