import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.billing import BillingError
from app.db import pool
from app.payments import settle_payment
from app.telegram_link import bot_start_url
from app.yookassa import YooKassaError

router = APIRouter()
log = logging.getLogger("app.yookassa_api")

_RETURN_PAGE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Оплата — Aimarket</title>
<style>
  body {{ margin: 0; background: #f4f1ea; color: #1c1915; font: 17px/1.5 "Segoe UI", sans-serif; }}
  main {{ max-width: 520px; margin: 12vh auto; padding: 24px; }}
</style></head>
<body><main><h1>{title}</h1><p>{text}</p></main></body></html>"""


@router.post("/webhook")
async def webhook(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {"ok": True}
    payment = body.get("object") if isinstance(body, dict) else None
    payment_id = payment.get("id") if isinstance(payment, dict) else ""
    if not payment_id:
        return {"ok": True}
    try:
        settle_payment(str(payment_id))
    except (YooKassaError, BillingError) as exc:
        log.warning("вебхук ЮKassa %s: %s", payment_id, exc)
        raise HTTPException(status_code=500, detail="retry") from exc
    return {"ok": True}


@router.get("/return")
def payment_return(topup: int = 0) -> RedirectResponse | HTMLResponse:
    if topup:
        with pool.connection() as conn:
            row = conn.execute("SELECT payment_id, status FROM topups WHERE id = %s", (topup,)).fetchone()
        if row and row["status"] != "paid" and row["payment_id"]:
            try:
                settle_payment(str(row["payment_id"]))
            except (YooKassaError, BillingError):
                pass
    url = bot_start_url(f"paid_{topup}" if topup else "")
    if url:
        return RedirectResponse(url, status_code=302)
    return HTMLResponse(_RETURN_PAGE.format(title="Оплата", text="Вернитесь в Telegram-бот Aimarket."))
