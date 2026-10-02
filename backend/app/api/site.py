from fastapi import APIRouter, HTTPException

from app.legal import legal_consent_data, legal_privacy_data
from app.offer import legal_offer_data
from app.settings_store import consent_url, offer_url, privacy_url
from app.telegram_link import bot_start_url, bot_username

router = APIRouter(tags=["site"])


@router.get("/site/config")
def site_config() -> dict:
    bot_url = bot_start_url("web")
    username = bot_username()
    return {
        "bot_url": bot_url,
        "bot_label": f"@{username}" if username else "Telegram-бот",
        "privacy_url": privacy_url() or "/privacy",
        "consent_url": consent_url() or "/consent",
        "offer_url": offer_url() or "/offer",
    }


@router.get("/site/legal/{page}")
def site_legal(page: str) -> dict:
    pages = {
        "privacy": legal_privacy_data,
        "consent": legal_consent_data,
        "offer": legal_offer_data,
    }
    render = pages.get(page)
    if render is None:
        raise HTTPException(status_code=404, detail="not found")
    return render()
