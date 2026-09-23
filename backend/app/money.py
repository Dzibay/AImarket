from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from app.config import settings
from app.settings_store import get_setting


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
