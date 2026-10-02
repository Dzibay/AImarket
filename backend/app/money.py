import json
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from app.config import settings
from app.settings_store import get_setting

DEFAULT_MIN_TOPUP_USD = Decimal("10")


def usd_price_rub() -> Decimal:
    raw = get_setting("usd_price_rub").strip().replace(",", ".")
    if raw:
        try:
            value = Decimal(raw)
        except Exception:
            value = Decimal(0)
        if value > 0:
            return value
    if settings.usd_price_kopecks > 0:
        return Decimal(settings.usd_price_kopecks) / Decimal(100)
    return Decimal(0)


def usd_to_units(usd: Decimal) -> int:
    return int(
        (usd * Decimal(settings.router_quota_per_unit)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def units_to_usd(units: int) -> Decimal:
    return (Decimal(int(units)) / Decimal(settings.router_quota_per_unit)).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


def rub_to_usd(amount_rub: Decimal) -> Decimal:
    price = usd_price_rub()
    if price <= 0:
        return Decimal(0)
    return (amount_rub / price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def min_topup_usd() -> Decimal:
    """Минимальное пополнение в $. Задаётся в админке, по умолчанию $10."""
    raw = get_setting("min_topup_usd").strip().replace(",", ".")
    if raw:
        try:
            value = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            value = Decimal(0)
        if value > 0:
            return value
    return DEFAULT_MIN_TOPUP_USD


def min_topup_rub() -> Decimal:
    price = usd_price_rub()
    if price <= 0:
        return Decimal(0)
    return (min_topup_usd() * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def bonus_tiers() -> list[dict]:
    """Бонусы к пополнению из админки: [{"min_usd": 100, "percent": 10}, ...], по возрастанию порога."""
    raw = get_setting("topup_bonuses").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return normalize_bonus_tiers(data)


def normalize_bonus_tiers(data: object) -> list[dict]:
    tiers: dict[Decimal, Decimal] = {}
    if not isinstance(data, list):
        return []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            threshold = Decimal(str(item.get("min_usd", "")).replace(",", ".")).quantize(Decimal("0.01"))
            percent = Decimal(str(item.get("percent", "")).replace(",", ".")).quantize(Decimal("0.01"))
        except Exception:
            continue
        if threshold <= 0 or percent <= 0 or percent > 1000:
            continue
        tiers[threshold] = percent
    return [
        {"min_usd": float(threshold), "percent": float(percent)}
        for threshold, percent in sorted(tiers.items())
    ]


def topup_bonus(amount_usd: Decimal, tiers: list[dict] | None = None) -> tuple[Decimal, Decimal]:
    """Возвращает (процент, бонус в $) для суммы пополнения — берётся самый высокий подходящий порог."""
    tiers = bonus_tiers() if tiers is None else tiers
    percent = Decimal(0)
    for tier in tiers:
        if amount_usd >= Decimal(str(tier["min_usd"])):
            percent = Decimal(str(tier["percent"]))
    if percent <= 0:
        return Decimal(0), Decimal(0)
    bonus = (amount_usd * percent / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return percent, bonus
