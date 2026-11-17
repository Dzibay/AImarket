"""Снимок цен router.cheap «с учётом типа баланса и источника». Запуск на сервере из корня проекта:

    docker compose exec -T backend python - < scripts/pricing_snapshot.py > pricing_snapshot.json

Формула та же, что в колонке на router.cheap/pricing:
  множитель = price_ratio источника / цена единицы баланса аккаунта
  (без источника: balance_price_numerator/denominator × min(group_ratio) × billing_multiplier),
  цена = цена каталога × множитель.
"""
import json
import sys

sys.path.insert(0, "/app")

from app.config import settings
from app.db import pool
from app.upstream import upstream


def _ratio(num, den):
    try:
        num, den = float(num), float(den)
    except (TypeError, ValueError):
        return None
    return num / den if num > 0 and den > 0 else None


def _group_multiplier(row: dict, group_ratio: dict) -> float:
    groups = row.get("enable_groups") if isinstance(row.get("enable_groups"), list) else []
    values = [float(group_ratio[g]) for g in groups if g in group_ratio]
    base = min(values) if values else 1.0
    return base * float(row.get("billing_multiplier") or 1)


def main() -> None:
    pool.open()
    with upstream._lock:
        upstream._ensure_login()
        payload = upstream._authed("GET", "/api/pricing")
    rows = payload.get("data") or []
    group_ratio = payload.get("group_ratio") or {}
    unit_price = _ratio(
        payload.get("balance_unit_price_numerator"),
        payload.get("balance_unit_price_denominator"),
    )

    default_source: dict[str, dict] = {}
    for source in payload.get("routing_sources") or []:
        for item in source.get("model_discounts") or []:
            if item.get("default"):
                default_source[item["model"]] = {
                    "tier": source.get("tier"),
                    "label": source.get("label"),
                    "price_ratio": item.get("price_ratio"),
                }

    per_unit = settings.router_quota_per_unit
    models = []
    for row in rows:
        name = row.get("model_name")
        if not name:
            continue
        source = default_source.get(name)
        if source and unit_price:
            mult = float(source["price_ratio"]) / unit_price
        else:
            own = _ratio(row.get("balance_price_numerator"), row.get("balance_price_denominator"))
            mult = own * _group_multiplier(row, group_ratio) if own is not None else None

        item = {
            "model": name,
            "endpoints": row.get("supported_endpoint_types") or [],
            "vendor_id": row.get("vendor_id"),
            "context": row.get("context_length"),
            "billing_mode": row.get("billing_mode") or "",
            "source": source,
            "balance_multiplier": mult,
        }
        if int(row.get("quota_type") or 0) == 1:
            price = float(row.get("model_price") or 0)
            item.update(
                kind="request",
                price_unit=row.get("price_unit") or "request",
                catalog_usd=price,
                balance_usd=price * mult if mult is not None else None,
            )
        else:
            inp = float(row.get("model_ratio") or 0) * 1_000_000 / per_unit
            out = inp * float(row.get("completion_ratio") or 1)
            cache = inp * float(row["cache_ratio"]) if row.get("cache_ratio") is not None else None
            item.update(
                kind="token",
                catalog_usd={"input": inp, "output": out, "cache": cache},
                balance_usd=(
                    {
                        "input": inp * mult,
                        "output": out * mult,
                        "cache": cache * mult if cache is not None else None,
                    }
                    if mult is not None
                    else None
                ),
            )
        models.append(item)

    models.sort(key=lambda m: m["model"])
    json.dump(
        {
            "balance_type": payload.get("balance_type"),
            "balance_unit_price": unit_price,
            "group_ratio": group_ratio,
            "models": models,
        },
        sys.stdout,
        ensure_ascii=False,
        indent=1,
    )


if __name__ == "__main__":
    main()
