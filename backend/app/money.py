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


def supplier_usd_price_rub() -> Decimal:
    """Курс $ у поставщика. Если не задан — берём клиентский курс."""
    raw = get_setting("supplier_usd_price_rub").strip().replace(",", ".")
    if raw:
        try:
            value = Decimal(raw)
        except Exception:
            value = Decimal(0)
        if value > 0:
            return value
    return usd_price_rub()


def supplier_api_usd_rate() -> Decimal:
    """Курс API-$ к реальным $ кабинета router.cheap: API-$ = реальные $ × rate.

    Ключи у поставщика списываются в реальных $ (limit_by_wallet_charge), поэтому
    квота ключа = API-$ клиента / rate, а баланс клиента = remain_quota × rate.
    """
    raw = get_setting("supplier_api_usd_rate").strip().replace(",", ".")
    if raw:
        try:
            # 6 знаков — как api_keys.quota_rate, иначе курс ключа никогда не совпадёт с настройкой.
            value = Decimal(raw).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        except Exception:
            value = Decimal(0)
        if value > 0:
            return value
    return Decimal("1")


def usd_to_units(usd: Decimal) -> int:
    """$ → единицы квоты router.cheap (без курса; для ключей — api_usd_to_real_units)."""
    return int(
        (usd * Decimal(settings.router_quota_per_unit)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def units_to_usd(units: int) -> Decimal:
    """Единицы квоты → $ без курса (сырой баланс кабинета, API-единицы журнала usage)."""
    return (Decimal(int(units)) / Decimal(settings.router_quota_per_unit)).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


def cabinet_to_api_usd(cabinet_usd: Decimal) -> Decimal:
    """Баланс кабинета поставщика → API-$ для дашборда."""
    rate = supplier_api_usd_rate()
    if rate == 1:
        return cabinet_usd
    return (cabinet_usd * rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def key_rate(value: object) -> Decimal:
    """Курс, по которому выставлена квота ключа. NULL/0 — старые ключи 1:1."""
    try:
        rate = Decimal(str(value)) if value not in (None, "") else Decimal(0)
    except Exception:
        rate = Decimal(0)
    return rate if rate > 0 else Decimal("1")


def api_usd_to_real_units(api_usd: Decimal, rate: Decimal) -> int:
    """API-$ клиента → единицы remain_quota (реальные $ кабинета)."""
    rate = key_rate(rate)
    return usd_to_units(Decimal(api_usd) / rate)


def real_units_to_api_usd(units: int, rate: Decimal) -> Decimal:
    """Единицы remain_quota (реальные $) → API-$ клиента."""
    rate = key_rate(rate)
    return (Decimal(int(units)) * rate / Decimal(settings.router_quota_per_unit)).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


def real_units_to_api_units(units: int, rate: Decimal) -> int:
    """Единицы журнала router.cheap (реальные $) → единицы API-$ для таблицы usage."""
    rate = key_rate(rate)
    return int((Decimal(int(units)) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


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


def referral_bonus_percent() -> Decimal:
    """Процент реферального бонуса с оплаты приглашённого (0 — программа без начислений)."""
    raw = get_setting("referral_bonus_percent").strip().replace(",", ".")
    if not raw:
        return Decimal(0)
    try:
        value = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal(0)
    if value < 0:
        return Decimal(0)
    if value > 100:
        return Decimal(100)
    return value
