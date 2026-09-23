import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from app.api.admin import router as admin_router
from app.api.products import router as products_router
from app.api.users import router as users_router
from app.api.yookassa import router as yookassa_router
from app.billing import sync_all
from app.config import settings
from app.db import ensure_schema, pool
from app.offer import render_offer
from app.settings_store import bootstrap_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app.main")
_stop = threading.Event()
_ADMIN_PAGE = Path(__file__).resolve().parent / "web" / "admin.html"


def _sync_loop() -> None:
    _stop.wait(5)
    while not _stop.is_set():
        try:
            sync_all()
        except Exception:
            log.exception("сверка балансов с router.cheap")
        _stop.wait(max(15, settings.sync_interval_sec))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not settings.bot_internal_token:
        log.warning("BOT_INTERNAL_TOKEN не задан — бот не сможет звать API")
    if not settings.admin_password:
        log.warning("ADMIN_PASSWORD не задан — вход в админку закрыт")
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        log.warning("YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY не заданы — оплата закрыта")
    ensure_schema()
    bootstrap_settings()
    worker = threading.Thread(target=_sync_loop, name="balance-sync", daemon=True)
    worker.start()
    yield
    _stop.set()
    pool.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def home() -> HTMLResponse:
    page = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<title>Aimarket</title>
<style>
  body { margin: 0; background: #f4f1ea; color: #1c1915; font: 16px/1.45 "Segoe UI", sans-serif; }
  main { max-width: 520px; margin: 15vh auto; padding: 24px; }
  a { color: inherit; }
</style></head>
<body><main><h1>Aimarket</h1><p><a href="/offer">Оферта</a></p><p><a href="/admin">Админка</a></p></main></body></html>"""
    return HTMLResponse(page)


@app.get("/offer")
def offer() -> HTMLResponse:
    return HTMLResponse(render_offer())


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(_ADMIN_PAGE)


app.include_router(products_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(yookassa_router, prefix="/api/yookassa")
