import logging
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

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
_WEB = Path(__file__).resolve().parent / "web"
_ADMIN_PAGE = _WEB / "admin-panel" / "index.html"
_STATIC_DIR = _WEB / "static"
_SETUP_DIR = _WEB / "downloads" / "setup"
_SETUP_NAME = re.compile(
    r"aimarket-[a-z0-9-]+-(windows|macos)-(ru|en)\.zip|setup-aimarket-[a-z0-9-]+-(ru|en)\.sh"
)
_STATIC_FILES = frozenset(
    p.name for p in _STATIC_DIR.iterdir() if p.is_file()
) if _STATIC_DIR.is_dir() else frozenset()
_FAVICON_LINKS = """
<link rel="icon" type="image/png" href="/favicon-96x96.png" sizes="96x96">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="shortcut icon" href="/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#1c1915">
""".strip()
_MEDIA = {
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webmanifest": "application/manifest+json",
}


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
    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>Aimarket</title>
  {_FAVICON_LINKS}
  <style>
    body {{ margin: 0; background: #f4f1ea; color: #1c1915; font: 16px/1.45 "Segoe UI", sans-serif; }}
    main {{ max-width: 520px; margin: 15vh auto; padding: 24px; }}
    a {{ color: inherit; }}
  </style>
</head>
<body>
  <main>
    <h1>Aimarket</h1>
    <p><a href="/offer">Оферта</a></p>
    <p><a href="/admin-panel">Админка</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(page)


@app.get("/offer")
def offer() -> HTMLResponse:
    return HTMLResponse(render_offer())


@app.get("/admin")
def admin_redirect() -> RedirectResponse:
    return RedirectResponse("/admin-panel", status_code=307)


@app.get("/admin-panel")
def admin_panel() -> FileResponse:
    return FileResponse(_ADMIN_PAGE)


@app.get("/downloads/setup/{name}")
def download_setup(name: str) -> FileResponse:
    if _SETUP_NAME.fullmatch(name) is None:
        raise HTTPException(status_code=404, detail="not found")
    path = _SETUP_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    media = "application/zip" if name.endswith(".zip") else "text/x-sh"
    return FileResponse(path, filename=name, media_type=media)


app.include_router(products_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(yookassa_router, prefix="/api/yookassa")


@app.get("/{filename}")
def root_static(filename: str) -> FileResponse:
    if filename not in _STATIC_FILES:
        raise HTTPException(status_code=404, detail="not found")
    path = _STATIC_DIR / filename
    return FileResponse(path, media_type=_MEDIA.get(path.suffix.lower()))
