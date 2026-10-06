import logging

import httpx

from app.config import settings

log = logging.getLogger("app.backend")


class BackendError(Exception):
    def __init__(self, status: int, detail: str = "") -> None:
        self.status = status
        self.detail = detail
        super().__init__(detail or f"backend {status}")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.backend_url.rstrip("/"),
        headers={"X-Bot-Token": settings.bot_internal_token},
        timeout=45.0,
    )


async def _request(method: str, path: str, json: dict | None = None) -> dict:
    try:
        async with _client() as client:
            response = await client.request(method, path, json=json)
    except httpx.HTTPError as exc:
        log.warning("backend недоступен: %s", exc)
        raise BackendError(0, "unavailable") from exc
    if response.status_code >= 400:
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                raw = body.get("detail") or ""
                detail = raw if isinstance(raw, str) else str(raw)
        except ValueError:
            detail = ""
        raise BackendError(response.status_code, detail)
    return response.json()


async def upsert_user(telegram_id: int, username: str, first_name: str) -> dict:
    return await _request(
        "POST",
        "/api/users",
        {"telegram_id": telegram_id, "username": username, "first_name": first_name},
    )


async def record_referral(telegram_id: int, token: str) -> dict:
    return await _request("POST", f"/api/users/{telegram_id}/referral", {"token": token})


async def get_user(telegram_id: int) -> dict:
    return await _request("GET", f"/api/users/{telegram_id}")


async def accept_offer(telegram_id: int) -> dict:
    return await _request("POST", f"/api/users/{telegram_id}/offer")


async def create_topup(telegram_id: int, amount_rub: float) -> dict:
    return await _request("POST", f"/api/users/{telegram_id}/topups", {"amount_rub": amount_rub})


async def check_topup(telegram_id: int, topup_id: int) -> dict:
    return await _request("POST", f"/api/users/{telegram_id}/topups/{topup_id}/check")


async def issue_key(telegram_id: int) -> dict:
    return await _request("POST", f"/api/users/{telegram_id}/keys")


async def read_key(telegram_id: int) -> dict:
    return await _request("GET", f"/api/users/{telegram_id}/key")


async def get_key_history(
    telegram_id: int,
    *,
    offset: int = 0,
    limit: int = 5,
) -> dict:
    params = f"?offset={offset}&limit={limit}"
    return await _request("GET", f"/api/users/{telegram_id}/key/history{params}")


async def install_command(telegram_id: int, app: str, os: str, action: str = "setup") -> dict:
    return await _request(
        "POST",
        f"/api/users/{telegram_id}/install",
        {"app": app, "os": os, "action": action},
    )


async def install_command(telegram_id: int, app: str, os: str, action: str = "setup") -> dict:
    return await _request(
        "POST",
        f"/api/users/{telegram_id}/install",
        {"app": app, "os": os, "action": action},
    )


async def reissue_key(telegram_id: int) -> dict:
    return await _request("POST", f"/api/users/{telegram_id}/keys/reissue")


async def list_products() -> list[dict]:
    data = await _request("GET", "/api/products")
    return list(data.get("items") or [])


async def toggle_notification(telegram_id: int, key: str) -> dict:
    return await _request(
        "POST",
        f"/api/users/{telegram_id}/notifications/toggle",
        {"key": key},
    )


async def get_history(
    telegram_id: int,
    *,
    filter: str = "all",
    offset: int = 0,
    limit: int = 5,
) -> dict:
    params = f"?filter={filter}&offset={offset}&limit={limit}"
    return await _request("GET", f"/api/users/{telegram_id}/history{params}")
