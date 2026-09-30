import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from app.config import settings
from app.money import usd_to_units, units_to_usd

log = logging.getLogger("app.upstream")

# /api/log/token жёстко лимитируется — после 429 не дергаем несколько минут.
_token_log_blocked_until = 0.0
_TOKEN_LOG_COOLDOWN_SEC = 300


class UpstreamError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class RouterCheap:
    """Сессия кабинета router.cheap: корневой ключ остаётся на сервере."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cookies: dict[str, str] = {}
        self._user_id = ""
        self._pricing_at = 0.0
        self._pricing: list[dict] = []

    def list_models(self) -> list[dict]:
        now = time.monotonic()
        if self._pricing and now - self._pricing_at < 600:
            return list(self._pricing)
        payload = self._public("GET", "/api/pricing")
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise UpstreamError("каталог router.cheap пуст")
        models = [_model_row(row) for row in rows if isinstance(row, dict) and row.get("model_name")]
        models.sort(key=lambda item: item["model_name"])
        self._pricing = models
        self._pricing_at = now
        return list(models)

    def clear_session(self) -> None:
        with self._lock:
            self._cookies.clear()
            self._user_id = ""

    def supplier_balance_usd(self) -> Decimal:
        with self._lock:
            self._ensure_login()
            return units_to_usd(self._balance_units())

    def get_token(self, token_id: int) -> dict | None:
        with self._lock:
            self._ensure_login()
            return self._token(token_id)

    def add_quota(self, token_id: int, extra_usd: Decimal) -> Decimal:
        extra_units = usd_to_units(extra_usd)
        if extra_units <= 0:
            raise UpstreamError("лимит ключа слишком маленький")
        with self._lock:
            self._ensure_login()
            current = self._token(token_id)
            if current is None:
                raise UpstreamError("ключ не найден")
            if extra_units > self._balance_units():
                raise UpstreamError("на router.cheap не хватает баланса")
            new_units = int(current.get("remain_quota") or 0) + extra_units
            self._put_quota(token_id, current, new_units)
        return units_to_usd(new_units)

    def update_quota(self, token_id: int, quota_usd: Decimal) -> None:
        units = usd_to_units(quota_usd)
        if units <= 0:
            raise UpstreamError("лимит ключа слишком маленький")
        with self._lock:
            self._ensure_login()
            current = self._token(token_id)
            if current is None:
                raise UpstreamError("ключ не найден")
            old_units = int(current.get("remain_quota") or 0)
            increase = units - old_units
            if increase > self._balance_units():
                raise UpstreamError("на router.cheap не хватает баланса")
            self._put_quota(token_id, current, units)

    def create_child_key(self, name: str, quota_usd: Decimal) -> tuple[int, str]:
        units = usd_to_units(quota_usd)
        if units <= 0:
            raise UpstreamError("лимит ключа слишком маленький")
        with self._lock:
            self._ensure_login()
            balance = self._balance_units()
            if units > balance:
                raise UpstreamError("на router.cheap не хватает баланса")
            self._authed(
                "POST",
                "/api/token/",
                {
                    "name": name,
                    "remain_quota": units,
                    "expired_time": -1,
                    "unlimited_quota": False,
                    "model_limits_enabled": False,
                    "model_limits": "",
                    "allow_ips": "",
                    "group": "default",
                    "cross_group_retry": False,
                },
            )
            token_id = self._find_token_id(name)
            try:
                revealed = self._authed("POST", f"/api/token/{token_id}/key", {})
            except UpstreamError:
                self._delete_quiet(token_id)
                raise
        secret = _secret_from(revealed)
        if not secret:
            self.delete_key(token_id)
            raise UpstreamError("router.cheap не вернул ключ")
        return token_id, secret

    def reveal_key(self, token_id: int) -> str:
        with self._lock:
            self._ensure_login()
            revealed = self._authed("POST", f"/api/token/{token_id}/key", {})
        secret = _secret_from(revealed)
        if not secret:
            raise UpstreamError("router.cheap не вернул ключ")
        return secret

    def spend_logs(
        self,
        token_secret: str,
        *,
        token_name: str = "",
        upstream_id: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict], bool]:
        """Журнал расходов: /api/log/self → /api/log/token (fallback).

        Второе значение — True, если следующих страниц нет.
        """
        page = max(1, page)
        if token_name:
            raw_items = self._spend_logs_by_self(token_name, page=page, page_size=page_size)
            if raw_items:
                if upstream_id is not None:
                    raw_items = [
                        item
                        for item in raw_items
                        if _log_belongs_to_token(item, token_name, upstream_id)
                    ]
                items = _consumption_logs(raw_items)
                if items:
                    return items, len(raw_items) < page_size
        if page == 1 and token_secret.strip():
            items = self._spend_logs_by_secret(token_secret)
            if items:
                return items, True
        return [], True

    def _spend_logs_by_secret(self, token_secret: str) -> list[dict]:
        if _token_log_cooled_down():
            return []
        key = _token_log_canonical(token_secret)
        if not key:
            return []
        query = urllib.parse.urlencode({"key": key})
        try:
            payload = self._public("GET", f"/api/log/token?{query}")
        except UpstreamError as exc:
            if "429" in exc.message:
                _mark_token_log_rate_limited()
                log.warning(
                    "журнал /api/log/token: rate limit, повтор не раньше чем через %s с",
                    _TOKEN_LOG_COOLDOWN_SEC,
                )
            else:
                log.warning("журнал router.cheap по ключу не прочитан: %s", exc.message)
            return []
        if isinstance(payload, dict) and payload.get("success") is False:
            log.warning(
                "журнал router.cheap по ключу: %s",
                payload.get("message") or "ошибка",
            )
            return []
        items = _consumption_logs(_token_items(payload))
        return items

    def _spend_logs_by_self(self, token_name: str, *, page: int, page_size: int) -> list[dict]:
        query = urllib.parse.urlencode(
            {
                "p": str(page),
                "page_size": str(page_size),
                "type": "2",
                "token_name": token_name,
            }
        )
        with self._lock:
            self._ensure_login()
            try:
                payload = self._authed("GET", f"/api/log/self?{query}")
            except UpstreamError as exc:
                log.warning("журнал router.cheap /api/log/self не прочитан: %s", exc.message)
                return []
        return _token_items(payload)

    def delete_key(self, token_id: int) -> None:
        with self._lock:
            self._ensure_login()
            self._authed("DELETE", f"/api/token/{token_id}")

    def set_token_enabled(self, token_id: int, enabled: bool) -> None:
        status = 1 if enabled else 2
        with self._lock:
            self._ensure_login()
            self._authed("PUT", "/api/token/?status_only=true", {"id": token_id, "status": status})

    def disable_key(self, token_id: int) -> None:
        self.set_token_enabled(token_id, False)

    def enable_key(self, token_id: int) -> None:
        self.set_token_enabled(token_id, True)

    def _delete_quiet(self, token_id: int) -> None:
        try:
            self._authed("DELETE", f"/api/token/{token_id}")
        except UpstreamError:
            log.warning("не удалось удалить ключ router.cheap id=%s", token_id)

    def _find_token_id(self, name: str) -> int:
        query = urllib.parse.urlencode({"keyword": name, "p": "1", "size": "20"})
        listed = self._authed("GET", f"/api/token/search?{query}")
        matches = [
            item
            for item in _token_items(listed)
            if item.get("name") == name and item.get("token_type") != "root"
        ]
        if not matches:
            listed = self._authed("GET", "/api/token/?p=1&size=50")
            matches = [
                item
                for item in _token_items(listed)
                if item.get("name") == name and item.get("token_type") != "root"
            ]
        if not matches:
            raise UpstreamError("созданный ключ не найден")
        return int(matches[0]["id"])

    def _put_quota(self, token_id: int, current: dict, units: int) -> None:
        self._authed(
            "PUT",
            "/api/token/",
            {
                "id": token_id,
                "name": current.get("name") or "",
                "remain_quota": units,
                "expired_time": current.get("expired_time") if current.get("expired_time") is not None else -1,
                "unlimited_quota": False,
                "model_limits_enabled": bool(current.get("model_limits_enabled")),
                "model_limits": current.get("model_limits") or "",
                "allow_ips": current.get("allow_ips") or "",
                "group": current.get("group") or "default",
                "cross_group_retry": bool(current.get("cross_group_retry")),
                "claude_routing_tier": current.get("claude_routing_tier") or "",
                "grok_routing_tier": current.get("grok_routing_tier") or "",
                "gpt_routing_tier": current.get("gpt_routing_tier") or "",
            },
        )

    def _root_key(self) -> str:
        from app.settings_store import get_setting

        return get_setting("router_root_key").strip() or settings.router_root_key.strip()

    def _token(self, token_id: int) -> dict | None:
        try:
            payload = self._authed("GET", f"/api/token/{token_id}")
        except UpstreamError as exc:
            text = exc.message.lower()
            if "404" in text or "not found" in text or "не найден" in text:
                return None
            raise
        data = payload.get("data")
        return data if isinstance(data, dict) else None

    def _balance_units(self) -> int:
        payload = self._authed("GET", "/api/user/self")
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict) or data.get("quota") is None:
            raise UpstreamError("не удалось прочитать баланс router.cheap")
        return int(data["quota"])

    def _ensure_login(self) -> None:
        if self._user_id and self._cookies:
            return
        root_key = self._root_key()
        if not root_key:
            raise UpstreamError("корневой ключ router.cheap не задан")
        payload = self._request("POST", "/api/user/login/key", {"key": root_key})
        data = payload.get("data") if isinstance(payload, dict) else None
        user_id = data.get("id") if isinstance(data, dict) else None
        if not user_id or not self._cookies:
            raise UpstreamError("не удалось войти в router.cheap")
        self._user_id = str(user_id)

    def _authed(self, method: str, path: str, body: dict | None = None) -> dict:
        try:
            return self._request(method, path, body, {"New-Api-User": self._user_id})
        except UpstreamError as exc:
            if "401" not in exc.message:
                raise
            self._cookies.clear()
            self._user_id = ""
            self._ensure_login()
            return self._request(method, path, body, {"New-Api-User": self._user_id})

    def _public(self, method: str, path: str) -> dict:
        return self._request(method, path, None, None, send_cookies=False)

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        headers: dict | None = None,
        send_cookies: bool = True,
    ) -> dict:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(settings.router_base_url.rstrip("/") + path, data=data, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "aimarket")
        if send_cookies and self._cookies:
            req.add_header("Cookie", "; ".join(f"{key}={value}" for key, value in self._cookies.items()))
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self._store_cookies(resp.headers)
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            self._store_cookies(exc.headers)
            raw = exc.read().decode("utf-8", "replace")
            log.warning("router.cheap %s %s -> %s", method, path, exc.code)
            raise UpstreamError(f"router.cheap {exc.code}: {raw[:180]}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            log.warning("router.cheap недоступен: %s", exc)
            raise UpstreamError("router.cheap недоступен") from exc
        if isinstance(payload, dict) and payload.get("success") is False:
            raise UpstreamError(str(payload.get("message") or "ошибка router.cheap"))
        return payload if isinstance(payload, dict) else {}

    def _store_cookies(self, headers) -> None:
        for item in headers.get_all("Set-Cookie") or []:
            pair = item.split(";", 1)[0]
            if "=" in pair:
                key, value = pair.split("=", 1)
                self._cookies[key] = value


def _secret_from(payload: dict) -> str:
    data = payload.get("data") if isinstance(payload, dict) else None
    raw = data.get("key") if isinstance(data, dict) else None
    if not isinstance(raw, str) or not raw:
        return ""
    return raw if raw.startswith("sk-") else f"sk-{raw}"


def _log_field(item: dict, *names: str) -> object | None:
    for name in names:
        if name in item and item[name] not in (None, ""):
            return item[name]
    return None


def _log_quota_units(item: dict) -> int:
    for field in ("quota", "quota_used", "amount"):
        raw = item.get(field)
        if raw in (None, ""):
            continue
        try:
            value = abs(int(float(raw)))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def _log_created_sort_key(value: object) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        stamp = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        if text.isdigit():
            stamp = int(text)
        else:
            return 0
    else:
        return 0
    if stamp > 10_000_000_000:
        stamp //= 1000
    return max(stamp, 0)


def _token_log_cooled_down() -> bool:
    return time.monotonic() < _token_log_blocked_until


def _mark_token_log_rate_limited() -> None:
    global _token_log_blocked_until
    _token_log_blocked_until = time.monotonic() + _TOKEN_LOG_COOLDOWN_SEC


def _token_log_canonical(token_secret: str) -> str:
    secret = token_secret.strip()
    if not secret:
        return ""
    return secret if secret.startswith("sk-") else f"sk-{secret}"


def _consumption_logs(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    for item in items:
        raw_type = item.get("type")
        if raw_type not in (None, ""):
            try:
                if int(raw_type) not in (2,):
                    continue
            except (TypeError, ValueError):
                pass
        units = _log_quota_units(item)
        if units <= 0 and not str(item.get("model_name") or "").strip():
            continue
        result.append(item)
    result.sort(key=lambda row: _log_created_sort_key(row.get("created_at")), reverse=True)
    return result


def _log_belongs_to_token(item: dict, token_name: str, upstream_id: int) -> bool:
    raw_id = item.get("token_id")
    if raw_id not in (None, ""):
        try:
            if int(raw_id) == upstream_id:
                return True
        except (TypeError, ValueError):
            pass
    return str(item.get("token_name") or "") == token_name


def _token_items(payload: dict) -> list[dict]:
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        items = data.get("items") or data.get("data") or []
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _model_row(row: dict) -> dict:
    name = str(row.get("model_name") or "")
    ratio = Decimal(str(row.get("model_ratio") or 0))
    completion = Decimal(str(row.get("completion_ratio") or 1))
    per_unit = Decimal(settings.router_quota_per_unit)
    input_per_million = ratio * Decimal(1_000_000) / per_unit
    output_per_million = input_per_million * completion
    request_usd = None
    if int(row.get("quota_type") or 0) == 1:
        request_usd = float(row.get("model_price") or 0)
        input_per_million = Decimal(0)
        output_per_million = Decimal(0)
    return {
        "model_name": name,
        "tiered": str(row.get("billing_mode") or "") not in {"", "ratio"},
        "input_usd_per_million": float(input_per_million),
        "output_usd_per_million": float(output_per_million),
        "request_usd": request_usd,
    }


upstream = RouterCheap()
