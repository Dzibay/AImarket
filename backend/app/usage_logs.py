"""Разбор строк журнала router.cheap / New API."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.upstream import _log_field, _log_quota_units

MSK = ZoneInfo("Europe/Moscow")


def upstream_log_id(item: dict) -> int | None:
    raw = _log_field(item, "id", "Id")
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def log_created_at(item: dict) -> datetime | None:
    raw = _log_field(item, "created_at", "CreatedAt", "create_time")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            number = None
        if number is not None and number > 0:
            raw = int(number)
        elif text.isdigit():
            raw = int(text)
        else:
            try:
                moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
            if moment.tzinfo is None:
                # router.cheap иногда отдаёт локальное время без offset — считаем MSK
                moment = moment.replace(tzinfo=MSK)
            return moment.astimezone(timezone.utc)
    try:
        stamp = int(float(raw))
    except (TypeError, ValueError):
        return None
    if stamp > 10_000_000_000:
        stamp //= 1000
    if stamp <= 0:
        return None
    return datetime.fromtimestamp(stamp, timezone.utc)


def parse_usage_log(item: dict) -> dict | None:
    """Нормализованная строка расхода или None, если запись неполная."""
    log_id = upstream_log_id(item)
    created_at = log_created_at(item)
    if log_id is None or created_at is None:
        return None
    model_name = str(_log_field(item, "model_name", "model") or "")
    try:
        prompt_tokens = int(_log_field(item, "prompt_tokens") or 0)
    except (TypeError, ValueError):
        prompt_tokens = 0
    try:
        completion_tokens = int(_log_field(item, "completion_tokens") or 0)
    except (TypeError, ValueError):
        completion_tokens = 0
    units = _log_quota_units(item)
    if units <= 0 and not model_name:
        return None
    return {
        "upstream_log_id": log_id,
        "model_name": model_name[:200],
        "prompt_tokens": max(prompt_tokens, 0),
        "completion_tokens": max(completion_tokens, 0),
        "quota_units": units,
        "created_at": created_at,
    }
