"""Сериализация дат для API — всегда UTC с явным offset."""

from datetime import datetime, timezone


def iso_utc(value: datetime | None) -> str:
    if value is None:
        return ""
    moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
