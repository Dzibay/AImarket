import hashlib
import logging
import secrets
import threading
from decimal import Decimal

from app.db import pool
from app.money import units_to_usd
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
        _store_key(user_id, name, secret, upstream_id, amount)
        return {"secret": secret, "base_url": _base_url(), "balance_usd": float(amount)}


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
            _set_balance(user_id, amount, "", "", 0, Decimal(0), write_ledger=False)
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
        _store_key(user_id, name, secret, new_id, amount)
        return {"secret": secret, "base_url": _base_url(), "balance_usd": float(amount)}


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
    _set_balance(user_id, amount, "", "", 0, Decimal(0), write_ledger=False)
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
    with pool.connection() as conn:
        row = conn.execute("SELECT COALESCE(SUM(balance_usd), 0) AS total FROM users").fetchone()
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
            SELECT id, upstream_id, prefix
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


def _store_key(user_id: int, name: str, secret: str, upstream_id: int, amount: Decimal) -> None:
    prefix = secret[:12]
    digest = hashlib.sha256(secret.encode()).hexdigest()
    try:
        with pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO api_keys (user_id, name, prefix, secret_hash, upstream_id, quota_usd)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, name, prefix, digest, upstream_id, amount),
            )
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


def _reraise(exc: UpstreamError) -> None:
    text = exc.message.lower()
    if "не хватает" in text:
        raise BillingError("supplier") from exc
    if "не задан" in text:
        raise BillingError("supplier") from exc
    raise BillingError("upstream") from exc
