import hashlib
import logging
import secrets
import threading
from datetime import datetime, timezone
from decimal import Decimal

from app.db import pool
from app.money import usd_to_units, units_to_usd
from app.upstream import UpstreamError, upstream

log = logging.getLogger("app.billing")
billing_lock = threading.RLock()


class BillingError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def sync_all() -> None:
    with billing_lock:
        with pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT user_id, upstream_id
                FROM api_keys
                WHERE revoked_at IS NULL AND upstream_id IS NOT NULL
                """
            ).fetchall()
        for row in rows:
            _sync_key(int(row["user_id"]), int(row["upstream_id"]))


def sync_user(user_id: int) -> None:
    with billing_lock:
        with pool.connection() as conn:
            row = conn.execute(
                """
                SELECT upstream_id
                FROM api_keys
                WHERE user_id = %s AND revoked_at IS NULL AND upstream_id IS NOT NULL
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return
        _sync_key(user_id, int(row["upstream_id"]))


def add_usd(user_id: int, amount: Decimal, kind: str, note: str, amount_kopecks: int = 0) -> Decimal:
    if amount <= 0:
        raise BillingError("empty")
    with billing_lock:
        if note:
            with pool.connection() as conn:
                existing = conn.execute(
                    "SELECT id FROM ledger WHERE kind = 'topup' AND note = %s",
                    (note,),
                ).fetchone()
            if existing is not None:
                return _balance(user_id)
        sync_all()
        _ensure_pool(amount)
        key = _active_key(user_id)
        if key is None:
            updated = (_balance(user_id) + amount).quantize(Decimal("0.0001"))
        else:
            try:
                updated = upstream.add_quota(int(key["upstream_id"]), amount)
            except UpstreamError as exc:
                _reraise(exc)
            _set_key_quota(int(key["id"]), updated)
        _set_balance(user_id, updated, kind, note, amount_kopecks, amount)
        return updated


def issue_key(user_id: int, telegram_id: int) -> dict:
    with billing_lock:
        _require_offer(user_id)
        if _active_key(user_id) is not None:
            raise BillingError("key-exists")
        sync_all()
        amount = _balance(user_id)
        if amount <= 0:
            raise BillingError("balance")
        _ensure_pool(Decimal(0))
        name = f"aimarket-{telegram_id}-{secrets.token_hex(3)}"
        try:
            upstream_id, secret = upstream.create_child_key(name, amount)
        except UpstreamError as exc:
            _reraise(exc)
        created_at = _store_key(user_id, name, secret, upstream_id, amount)
        return {
            "secret": secret,
            "base_url": _base_url(),
            "balance_usd": float(amount),
            "created_at": created_at.isoformat(),
        }


def reissue_key(user_id: int, telegram_id: int) -> dict:
    with billing_lock:
        _require_offer(user_id)
        key = _active_key(user_id)
        if key is None:
            raise BillingError("no-key")
        upstream_id = int(key["upstream_id"])
        try:
            token = upstream.get_token(upstream_id)
        except UpstreamError as exc:
            _reraise(exc)
        if token is not None:
            amount = units_to_usd(int(token.get("remain_quota") or 0))
            _record_balance(user_id, amount)
        else:
            amount = _balance(user_id)
        if amount <= 0:
            raise BillingError("empty")
        try:
            upstream.delete_key(upstream_id)
        except UpstreamError as exc:
            if "не найден" not in exc.message.lower() and "not found" not in exc.message.lower():
                _reraise(exc)
        _revoke_key(int(key["id"]))
        name = f"aimarket-{telegram_id}-{secrets.token_hex(3)}"
        try:
            new_id, secret = upstream.create_child_key(name, amount)
        except UpstreamError as exc:
            log.warning("перевыпуск не создал новый ключ, лимит сохранён у пользователя %s", user_id)
            raise BillingError("reissue-failed") from exc
        created_at = _store_key(user_id, name, secret, new_id, amount)
        return {
            "secret": secret,
            "base_url": _base_url(),
            "balance_usd": float(amount),
            "created_at": created_at.isoformat(),
        }


def describe_key(user_id: int) -> dict:
    with billing_lock:
        key = _active_key(user_id)
        if key is None:
            raise BillingError("no-key")
        secret = str(key["secret"] or "")
        if not secret:
            try:
                secret = upstream.reveal_key(int(key["upstream_id"]))
            except UpstreamError as exc:
                _reraise(exc)
            with pool.connection() as conn:
                conn.execute("UPDATE api_keys SET secret = %s WHERE id = %s", (secret, key["id"]))
        created_at = key["created_at"]
        return {
            "secret": secret,
            "prefix": key["prefix"],
            "base_url": _base_url(),
            "balance_usd": float(_balance(user_id)),
            "created_at": created_at.isoformat() if created_at is not None else "",
        }


def _sync_key(user_id: int, upstream_id: int) -> None:
    try:
        token = upstream.get_token(upstream_id)
    except UpstreamError as exc:
        log.warning("не удалось сверить ключ %s: %s", upstream_id, exc.message)
        return
    if token is None:
        with pool.connection() as conn:
            conn.execute(
                "UPDATE api_keys SET revoked_at = NOW() WHERE upstream_id = %s AND revoked_at IS NULL",
                (upstream_id,),
            )
        return
    amount = units_to_usd(int(token.get("remain_quota") or 0))
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT u.balance_usd, k.id, k.name
            FROM users u
            JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL
            WHERE u.id = %s AND k.upstream_id = %s
            """,
            (user_id, upstream_id),
        ).fetchone()
    key_id = int(row["id"]) if row else None
    token_name = str((row or {}).get("name") or token.get("name") or "")
    spent = _import_usage(user_id, key_id, upstream_id, token_name)
    # Падение лимита без записи в журнале router.cheap — это правка квоты, не запрос.
    with pool.connection() as conn:
        conn.execute(
            "DELETE FROM usage WHERE user_id = %s AND upstream_log_id IS NULL",
            (user_id,),
        )
    _record_balance(user_id, amount, spent)
    _warn_if_usage_differs(key_id, token)
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE api_keys
            SET quota_usd = %s
            WHERE upstream_id = %s AND revoked_at IS NULL
            """,
            (amount, upstream_id),
        )


def _ensure_pool(extra: Decimal) -> None:
    # Баланс на уже выпущенном ключе уже списан со счёта поставщика.
    # Сверяем только деньги, которые ещё предстоит оттуда забрать.
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(u.balance_usd), 0) AS total
            FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM api_keys k
                WHERE k.user_id = u.id AND k.revoked_at IS NULL AND k.upstream_id IS NOT NULL
            )
            """
        ).fetchone()
    promised = Decimal(row["total"]) + extra
    try:
        master = upstream.supplier_balance_usd()
    except UpstreamError as exc:
        _reraise(exc)
    if promised > master + Decimal("0.01"):
        raise BillingError("supplier")


def _require_offer(user_id: int) -> None:
    with pool.connection() as conn:
        row = conn.execute("SELECT offer_accepted_at FROM users WHERE id = %s", (user_id,)).fetchone()
    if row is None or row["offer_accepted_at"] is None:
        raise BillingError("offer")


def _active_key(user_id: int) -> dict | None:
    with pool.connection() as conn:
        return conn.execute(
            """
            SELECT id, upstream_id, prefix, secret, created_at
            FROM api_keys
            WHERE user_id = %s AND revoked_at IS NULL AND upstream_id IS NOT NULL
            """,
            (user_id,),
        ).fetchone()


def _balance(user_id: int) -> Decimal:
    with pool.connection() as conn:
        row = conn.execute("SELECT balance_usd FROM users WHERE id = %s", (user_id,)).fetchone()
    if row is None:
        raise BillingError("balance")
    return Decimal(row["balance_usd"])


def _record_balance(user_id: int, amount: Decimal, spent: Decimal | None = None) -> None:
    """Сверяет локальный баланс с остатком ключа.

    Уменьшение, подтверждённое новыми строками журнала, — расход.
    Остальная разница — ручное изменение лимита, оно не увеличивает расход.
    """
    current = _balance(user_id)
    delta = (current - amount).quantize(Decimal("0.0001"))
    if spent is None:
        consumed = delta if delta > 0 else Decimal(0)
    else:
        consumed = min(max(spent, Decimal(0)), delta) if delta > 0 else Decimal(0)
        consumed = consumed.quantize(Decimal("0.0001"))
    adjustment = (consumed - delta).quantize(Decimal("0.0001"))
    with pool.connection() as conn:
        conn.execute("UPDATE users SET balance_usd = %s WHERE id = %s", (amount, user_id))
        if consumed > 0:
            conn.execute(
                """
                INSERT INTO ledger (user_id, amount_kopecks, kind, note, amount_usd)
                VALUES (%s, 0, 'spend', 'расход', %s)
                """,
                (user_id, consumed),
            )
        if adjustment != 0:
            conn.execute(
                """
                INSERT INTO ledger (user_id, amount_kopecks, kind, note, amount_usd)
                VALUES (%s, 0, 'adjust', 'изменение лимита', %s)
                """,
                (user_id, adjustment),
            )


def _set_balance(
    user_id: int,
    amount: Decimal,
    kind: str,
    note: str,
    amount_kopecks: int,
    delta_usd: Decimal,
    write_ledger: bool = True,
) -> None:
    with pool.connection() as conn:
        conn.execute("UPDATE users SET balance_usd = %s WHERE id = %s", (amount, user_id))
        if write_ledger and kind:
            conn.execute(
                """
                INSERT INTO ledger (user_id, amount_kopecks, kind, note, amount_usd)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, amount_kopecks, kind, note, delta_usd),
            )


def _set_key_quota(key_id: int, amount: Decimal) -> None:
    with pool.connection() as conn:
        conn.execute("UPDATE api_keys SET quota_usd = %s WHERE id = %s", (amount, key_id))


def _revoke_key(key_id: int) -> None:
    with pool.connection() as conn:
        conn.execute("UPDATE api_keys SET revoked_at = NOW() WHERE id = %s", (key_id,))


def _store_key(user_id: int, name: str, secret: str, upstream_id: int, amount: Decimal) -> datetime:
    prefix = secret[:12]
    digest = hashlib.sha256(secret.encode()).hexdigest()
    try:
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO api_keys (user_id, name, prefix, secret_hash, secret, upstream_id, quota_usd)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING created_at
                """,
                (user_id, name, prefix, digest, secret, upstream_id, amount),
            ).fetchone()
        return row["created_at"]
    except Exception:
        try:
            upstream.delete_key(upstream_id)
        except UpstreamError:
            log.warning("ключ router.cheap %s остался после ошибки записи", upstream_id)
        raise


def _base_url() -> str:
    return upstream_base()


def upstream_base() -> str:
    from app.config import settings

    return settings.router_base_url.rstrip("/") + "/v1"


def _import_usage(user_id: int, key_id: int | None, upstream_id: int, token_name: str) -> Decimal:
    if not token_name or key_id is None:
        return Decimal(0)
    inserted_units = 0
    try:
        for page in range(10):
            items = upstream.spend_logs(token_name, page)
            if not items:
                break
            matched = [item for item in items if _log_matches(item, token_name, upstream_id)]
            if not matched:
                break
            page_units, seen_old = _save_usage_page(user_id, key_id, matched)
            inserted_units += page_units
            if seen_old or len(items) < 100:
                break
    except UpstreamError as exc:
        log.warning("журнал расходов router.cheap не прочитан: %s", exc.message)
    return units_to_usd(inserted_units)


def _log_matches(item: dict, token_name: str, upstream_id: int) -> bool:
    raw_id = item.get("token_id")
    if raw_id not in (None, ""):
        try:
            if int(raw_id) == upstream_id:
                return True
        except (TypeError, ValueError):
            pass
    return str(item.get("token_name") or "") == token_name


def _save_usage_page(user_id: int, key_id: int, items: list[dict]) -> tuple[int, bool]:
    ids = [int(item["id"]) for item in items if str(item.get("id") or "").isdigit() or isinstance(item.get("id"), int)]
    if not ids:
        return 0, False
    with pool.connection() as conn:
        known = {
            int(row["upstream_log_id"])
            for row in conn.execute(
                "SELECT upstream_log_id FROM usage WHERE upstream_log_id = ANY(%s)",
                (ids,),
            ).fetchall()
        }
        inserted_units = 0
        for item in items:
            log_id = item.get("id")
            if not isinstance(log_id, int) and not str(log_id or "").isdigit():
                continue
            log_id = int(log_id)
            if log_id in known:
                continue
            units = int(item.get("quota") or 0)
            if units < 0:
                units = 0
            _insert_usage(
                user_id,
                key_id,
                log_id,
                str(item.get("model_name") or ""),
                int(item.get("prompt_tokens") or 0),
                int(item.get("completion_tokens") or 0),
                units,
                _log_time(item.get("created_at")),
                conn,
            )
            inserted_units += units
    return inserted_units, bool(known)


def _warn_if_usage_differs(key_id: int | None, token: dict) -> None:
    raw_used = token.get("used_quota")
    if key_id is None or raw_used in (None, ""):
        return
    try:
        official = int(raw_used)
    except (TypeError, ValueError):
        return
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(quota_units), 0) AS units FROM usage WHERE api_key_id = %s",
            (key_id,),
        ).fetchone()
    logged = int(row["units"] or 0)
    if logged != official:
        log.warning(
            "расход ключа %s не совпал с router.cheap: журнал %s, used_quota %s",
            key_id,
            logged,
            official,
        )


def _log_time(value: object) -> datetime:
    try:
        stamp = int(value or 0)
    except (TypeError, ValueError):
        stamp = 0
    if stamp > 10_000_000_000:
        stamp //= 1000
    if stamp <= 0:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(stamp, timezone.utc)


def _insert_usage(
    user_id: int,
    key_id: int,
    upstream_log_id: int | None,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    quota_units: int,
    created_at: datetime,
    conn=None,
) -> None:
    sql = """
        INSERT INTO usage (
            user_id, api_key_id, upstream_log_id, model_name,
            prompt_tokens, completion_tokens, quota_units, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    if upstream_log_id is not None:
        sql += " ON CONFLICT (upstream_log_id) WHERE upstream_log_id IS NOT NULL DO NOTHING"
    params = (
        user_id,
        key_id,
        upstream_log_id,
        model_name[:200],
        max(prompt_tokens, 0),
        max(completion_tokens, 0),
        quota_units,
        created_at,
    )
    if conn is None:
        with pool.connection() as own:
            own.execute(sql, params)
    else:
        conn.execute(sql, params)


def _reraise(exc: UpstreamError) -> None:
    text = exc.message.lower()
    if "не хватает" in text:
        raise BillingError("supplier") from exc
    if "не задан" in text:
        raise BillingError("supplier") from exc
    raise BillingError("upstream") from exc
