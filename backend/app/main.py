import logging
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.api.admin import router as admin_router
from app.api.products import router as products_router
from app.api.site import router as site_router
from app.api.users import router as users_router
from app.api.web import router as web_router
from app.api.yookassa import router as yookassa_router
from app.billing import sync_all
from app.reminders import send_offer_reminders
from app.config import settings
from app.db import ensure_schema, pool
from app.settings_store import bootstrap_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app.main")
_stop = threading.Event()
_WEB = Path(__file__).resolve().parent / "web"
_SETUP_DIR = _WEB / "downloads" / "setup"
_SETUP_NAME = re.compile(
    r"aimarket-[a-z0-9-]+-(windows|macos)-(ru|en)\.zip|setup-aimarket-[a-z0-9-]+-(ru|en)\.sh"
)
def _sync_loop() -> None:
    _stop.wait(5)
    while not _stop.is_set():
        try:
            sync_all()
        except Exception:
            log.exception("сверка балансов с router.cheap")
        _stop.wait(max(15, settings.sync_interval_sec))


def _reminder_loop() -> None:
    _stop.wait(30)
    while not _stop.is_set():
        try:
            send_offer_reminders()
        except Exception:
            log.exception("напоминания об оферте")
        _stop.wait(120)


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
    threading.Thread(target=_sync_loop, name="balance-sync", daemon=True).start()
    threading.Thread(target=_reminder_loop, name="offer-reminders", daemon=True).start()
    yield
    _stop.set()
    pool.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/downloads/setup/{name}")
def download_setup(name: str) -> FileResponse:
    if _SETUP_NAME.fullmatch(name) is None:
        raise HTTPException(status_code=404, detail="not found")
    path = _SETUP_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    media = "application/zip" if name.endswith(".zip") else "text/x-sh"
    return FileResponse(path, filename=name, media_type=media)


app.include_router(site_router, prefix="/api")
app.include_router(web_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(yookassa_router, prefix="/api/yookassa")
