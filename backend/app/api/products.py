from fastapi import APIRouter, Depends, HTTPException

from app.money import usd_price_rub
from app.security import require_bot
from app.upstream import UpstreamError, upstream

router = APIRouter(dependencies=[Depends(require_bot)])


def _rub(value: float) -> str:
    if value >= 1 or value == 0:
        return f"{value:.2f}"
    return f"{value:.4g}"


def _price_label(item: dict, rub_per_usd: float) -> str:
    if rub_per_usd <= 0:
        return ""
    if item.get("request_usd") is not None:
        rub = float(item["request_usd"]) * rub_per_usd
        unit = "за секунду" if item.get("price_unit") == "second" else "за запрос"
        return f"{_rub(rub)} ₽ {unit}"
    prompt = float(item["input_usd_per_million"]) * rub_per_usd
    completion = float(item["output_usd_per_million"]) * rub_per_usd
    label = f"вход {_rub(prompt)} ₽ / 1M, выход {_rub(completion)} ₽ / 1M"
    if item.get("tiered"):
        label += ", зависит от длины контекста"
    return label


@router.get("/products")
def list_products() -> dict:
    try:
        models = upstream.list_models()
    except UpstreamError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    rub_per_usd = float(usd_price_rub())
    return {
        "items": [
            {
                "model_name": item["model_name"],
                "price_label": _price_label(item, rub_per_usd),
                "input_usd_per_million": item.get("input_usd_per_million"),
                "output_usd_per_million": item.get("output_usd_per_million"),
                "request_usd": item.get("request_usd"),
            }
            for item in models
        ]
    }
