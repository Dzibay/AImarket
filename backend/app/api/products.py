from fastapi import APIRouter, Depends, HTTPException

from app.money import usd_price_rub
from app.security import require_bot
from app.upstream import UpstreamError, upstream

router = APIRouter(dependencies=[Depends(require_bot)])


def _price_label(item: dict, rub_per_usd: float) -> str:
    if rub_per_usd <= 0:
        return ""
    if item.get("request_usd") is not None:
        rub = float(item["request_usd"]) * rub_per_usd
        return f"{rub:.2f} ₽ за запрос"
    prompt = float(item["input_usd_per_million"]) * rub_per_usd
    completion = float(item["output_usd_per_million"]) * rub_per_usd
    label = f"вход {prompt:.2f} ₽ / 1M, выход {completion:.2f} ₽ / 1M"
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
            {"model_name": item["model_name"], "price_label": _price_label(item, rub_per_usd)}
            for item in models
        ]
    }
