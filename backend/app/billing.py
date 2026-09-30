import hashlib
import logging
import secrets
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal

from app.datetime_util import iso_utc
from app.db import pool
from app.money import usd_to_units, units_to_usd
from app.upstream import UpstreamError, upstream
from app.usage_logs import parse_usage_log
from app.usage_stats import usage_period_stats

log = logging.getLogger("app.billing")
billing_lock = threading.RLock()
_user_sync_at: dict[int, float] = {}
_USER_SYNC_MIN_SEC = 45


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
    from app.notifications import check_low_balance_users

    check_low_balance_users()


def sync_user(user_id: int, *, force: bool = False) -> None:
    if not force:
        now = time.monotonic()
        last = _user_sync_at.get(user_id, 0.0)
        if now - last < _USER_SYNC_MIN_SEC:
            return
    with billing_lock:
        if not force:
            now = time.monotonic()
            last = _user_sync_at.get(user_id, 0.0)
            if now - last < _USER_SYNC_MIN_SEC:
                return
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
        _sync_key(user_id, int(row["upstream_id"]), force=force)
        _user_sync_at[user_id] = time.monotonic()


def block_user(user_id: int, reason: str = "") -> None:
    with billing_lock:
        if not _user_exists(user_id):
            raise BillingError("user")
        if _is_blocked(user_id):
            return
        sync_user(user_id, force=True)
        key = _active_key(user_id)
        if key is not None:
            try:
                upstream.disable_key(int(key["upstream_id"]))
            except UpstreamError as exc:
                _reraise(exc)
        with pool.connection() as conn:
            conn.execute(
                "UPDATE users SET blocked_at = NOW(), blocked_reason = %s WHERE id = %s",
                (reason.strip()[:500], user_id),
            )


def unblock_user(user_id: int) -> None:
    with billing_lock:
        if not _user_exists(user_id):
            raise BillingError("user")
        if not _is_blocked(user_id):
            return
        key = _active_key(user_id)
        if key is not None:
            try:
                upstream.enable_key(int(key["upstream_id"]))
            except UpstreamError as exc:
                _reraise(exc)
        with pool.connection() as conn:
            conn.execute(
                "UPDATE users SET blocked_at = NULL, blocked_reason = '' WHERE id = %s",
                (user_id,),
            )


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
            from app.notifications import clear_limit_alert

            clear_limit_alert(int(key["id"]))
        from app.notifications import clear_low_balance_alert

        clear_low_balance_alert(user_id)
        _set_balance(user_id, updated, kind, note, amount_kopecks, amount)
        return updated


def issue_key(user_id: int, telegram_id: int) -> dict:
    with billing_lock:
        _require_not_blocked(user_id)
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
        key = _active_key(user_id)
        stats = _key_stats(user_id, int(key["id"]), upstream_id, amount) if key else {}
        return {
            "secret": secret,
            "base_url": _base_url(),
            "balance_usd": float(amount),
            "created_at": created_at.isoformat(),
            **stats,
        }


def reissue_key(user_id: int, telegram_id: int) -> dict:
    with billing_lock:
        _require_not_blocked(user_id)
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
        key = _active_key(user_id)
        stats = _key_stats(user_id, int(key["id"]), new_id, amount) if key else {}
        return {
            "secret": secret,
            "base_url": _base_url(),
            "balance_usd": float(amount),
            "created_at": created_at.isoformat(),
            **stats,
        }


def describe_key(user_id: int) -> dict:
    with billing_lock:
        _require_not_blocked(user_id)
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
        upstream_id = int(key["upstream_id"]) if key["upstream_id"] else None
        with pool.connection() as conn:
            quota_row = conn.execute(
                "SELECT quota_usd FROM api_keys WHERE id = %s",
                (key["id"],),
            ).fetchone()
        quota = Decimal(quota_row["quota_usd"] or 0) if quota_row else Decimal(0)
        stats = _key_stats(user_id, int(key["id"]), upstream_id, quota)
        return {
            "secret": secret,
            "prefix": key["prefix"],
            "base_url": _base_url(),
            "balance_usd": float(_balance(user_id)),
            "created_at": created_at.isoformat() if created_at is not None else "",
            **stats,
        }


def _sync_key(user_id: int, upstream_id: int, *, force: bool = False) -> None:
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
            SELECT u.balance_usd, k.id, k.name, k.secret
            FROM users u
            JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL
            WHERE u.id = %s AND k.upstream_id = %s
            """,
            (user_id, upstream_id),
        ).fetchone()
    key_id = int(row["id"]) if row else None
    token_name = str((row or {}).get("name") or token.get("name") or "")
    token_secret = str((row or {}).get("secret") or "")
    if not token_secret and key_id is not None:
        try:
            token_secret = upstream.reveal_key(upstream_id)
            with pool.connection() as conn:
                conn.execute("UPDATE api_keys SET secret = %s WHERE id = %s", (token_secret, key_id))
        except UpstreamError as exc:
            log.warning("не удалось получить секрет ключа %s: %s", upstream_id, exc.message)
    spent, new_usages = _import_usage(
        user_id,
        key_id,
        upstream_id,
        token_name,
        token_secret=token_secret,
        force=force,
    )
    if key_id is not None:
        with pool.connection() as conn:
            _attach_usage_to_key(user_id, key_id, conn)
    # Падение лимита без записи в журнале router.cheap — это правка квоты, не запрос.
    with pool.connection() as conn:
        conn.execute(
            "DELETE FROM usage WHERE user_id = %s AND upstream_log_id IS NULL",
            (user_id,),
        )
    _record_balance(user_id, amount, spent)
    _warn_if_usage_differs(user_id, token)
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE api_keys
            SET quota_usd = %s
            WHERE upstream_id = %s AND revoked_at IS NULL
            """,
            (amount, upstream_id),
        )
    with pool.connection() as conn:
        user_row = conn.execute(
            "SELECT telegram_id FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    telegram_id = int(user_row["telegram_id"]) if user_row else 0
    key_label = token_name
    if key_id is not None:
        with pool.connection() as conn:
            key_row = conn.execute(
                "SELECT prefix, secret, quota_usd FROM api_keys WHERE id = %s",
                (key_id,),
            ).fetchone()
        if key_row is not None:
            secret = str(key_row.get("secret") or "")
            prefix = str(key_row.get("prefix") or "")
            if len(secret) > 12:
                key_label = f"{secret[:8]}...{secret[-4:]}"
            elif prefix:
                key_label = prefix
            limit_usd = units_to_usd(int(token.get("used_quota") or 0)) + amount
        else:
            limit_usd = amount
    else:
        limit_usd = amount
    from app.notifications import process_balance_alerts, process_new_usages

    with pool.connection() as conn:
        balance_row = conn.execute(
            "SELECT balance_usd FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    user_balance = Decimal(balance_row["balance_usd"]) if balance_row else amount
    process_new_usages(user_id, telegram_id, key_id, new_usages, user_balance)
    process_balance_alerts(
        user_id,
        telegram_id,
        key_id,
        amount,
        limit_usd,
        key_label=key_label,
    )
    if _is_blocked(user_id):
        try:
            status = int(token.get("status") or 1)
        except (TypeError, ValueError):
            status = 1
        if status != 2:
            try:
                upstream.disable_key(upstream_id)
            except UpstreamError as exc:
                log.warning(
                    "не удалось отключить ключ %s у заблокированного пользователя %s: %s",
                    upstream_id,
                    user_id,
                    exc.message,
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


def _require_not_blocked(user_id: int) -> None:
    if _is_blocked(user_id):
        raise BillingError("blocked")


def _is_blocked(user_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute("SELECT blocked_at FROM users WHERE id = %s", (user_id,)).fetchone()
    return row is not None and row["blocked_at"] is not None


def _user_exists(user_id: int) -> bool:
    with pool.connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
    return row is not None


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


def _attach_usage_to_key(user_id: int, key_id: int, conn) -> None:
    conn.execute(
        """
        UPDATE usage
        SET api_key_id = %s
        WHERE user_id = %s AND (api_key_id IS DISTINCT FROM %s)
        """,
        (key_id, user_id, key_id),
    )


def _key_stats(user_id: int, key_id: int, upstream_id: int | None, quota_usd: Decimal) -> dict:
    remain = quota_usd
    used = Decimal(0)
    if upstream_id:
        try:
            token = upstream.get_token(upstream_id)
            if token:
                remain = units_to_usd(int(token.get("remain_quota") or 0))
                used = units_to_usd(int(token.get("used_quota") or 0))
        except UpstreamError:
            pass
    with pool.connection() as conn:
        stats = usage_period_stats(conn, user_id)
    spent_logs = units_to_usd(int(stats["spent_units"]))
    if spent_logs > used:
        used = spent_logs
    limit = (remain + used).quantize(Decimal("0.01"))
    last = stats["last_request_at"]
    return {
        "quota_usd": float(remain),
        "spent_usd": float(used),
        "limit_usd": float(limit),
        "prompt_tokens": stats["prompt_tokens"],
        "completion_tokens": stats["completion_tokens"],
        "last_request_at": iso_utc(last),
        "spent_today_usd": stats["spent_today_usd"],
        "spent_month_usd": stats["spent_month_usd"],
        "spent_week_usd": stats["spent_week_usd"],
        "spent_today_date": stats["spent_today_date"],
    }


def _base_url() -> str:
    return upstream_base()


def upstream_base() -> str:
    from app.config import settings

    return settings.router_base_url.rstrip("/") + "/v1"


def _import_usage(
    user_id: int,
    key_id: int | None,
    upstream_id: int,
    token_name: str,
    *,
    token_secret: str = "",
    force: bool = False,
) -> tuple[Decimal, list[dict]]:
    if key_id is None:
        return Decimal(0), []
    if not token_secret.strip():
        log.warning(
            "импорт расходов user=%s: секрет ключа не сохранён, задайте root в админке или перевыпустите ключ",
            user_id,
        )
        return Decimal(0), []
    inserted_units = 0
    new_usages: list[dict] = []
    page = 1
    try:
        while page <= 20:
            items, complete = upstream.spend_logs(
                token_secret,
                token_name=token_name,
                upstream_id=upstream_id,
                page=page,
                force=force,
            )
            if items:
                page_units, page_done, page_usages = _save_usage_page(user_id, key_id, items)
                inserted_units += page_units
                new_usages.extend(page_usages)
                if page_done:
                    break
            if complete:
                break
            page += 1
        if inserted_units:
            log.info(
                "импортировано %s записей расходов для ключа %s (user=%s)",
                len(new_usages),
                token_name or key_id,
                user_id,
            )
        elif page == 1:
            log.warning(
                "журнал расходов пуст для user=%s (ключ %s): проверьте секрет в БД и /api/log/token",
                user_id,
                token_name or key_id,
            )
    except UpstreamError as exc:
        log.warning("журнал расходов router.cheap не прочитан: %s", exc.message)
    return units_to_usd(inserted_units), new_usages


def _usage_notice(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    units: int,
) -> dict:
    return {
        "model_name": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "amount_usd": float(units_to_usd(units)),
    }


def _patch_usage_row(
    conn,
    *,
    row_id: int,
    key_id: int,
    units: int,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    created_at: datetime,
) -> int:
    """Обновляет строку расхода. Возвращает итоговые quota_units."""
    prev = conn.execute(
        "SELECT quota_units FROM usage WHERE id = %s",
        (row_id,),
    ).fetchone()
    prev_units = int(prev["quota_units"] or 0) if prev else 0
    conn.execute(
        """
        UPDATE usage
        SET api_key_id = %s,
            quota_units = CASE WHEN %s > 0 THEN %s ELSE quota_units END,
            model_name = CASE WHEN %s <> '' THEN %s ELSE model_name END,
            prompt_tokens = CASE WHEN %s > 0 THEN %s ELSE prompt_tokens END,
            completion_tokens = CASE WHEN %s > 0 THEN %s ELSE completion_tokens END,
            created_at = %s
        WHERE id = %s
        """,
        (
            key_id,
            units,
            units,
            model_name,
            model_name,
            prompt_tokens,
            prompt_tokens,
            completion_tokens,
            completion_tokens,
            created_at,
            row_id,
        ),
    )
    return units if units > 0 else prev_units


def _save_usage_page(user_id: int, key_id: int, items: list[dict]) -> tuple[int, bool, list[dict]]:
    parsed: list[dict] = []
    for item in items:
        row = parse_usage_log(item)
        if row is not None:
            parsed.append(row)
    if not parsed:
        return 0, True, []

    inserted_units = 0
    new_usages: list[dict] = []
    with pool.connection() as conn:
        for row in parsed:
            log_id = int(row["upstream_log_id"])
            units = int(row["quota_units"])
            model_name = str(row["model_name"])
            prompt_tokens = int(row["prompt_tokens"])
            completion_tokens = int(row["completion_tokens"])
            created_at = row["created_at"]

            prev = conn.execute(
                """
                SELECT id, quota_units
                FROM usage
                WHERE user_id = %s AND upstream_log_id = %s
                """,
                (user_id, log_id),
            ).fetchone()

            if prev is not None:
                prev_units = int(prev["quota_units"] or 0)
                effective = _patch_usage_row(
                    conn,
                    row_id=int(prev["id"]),
                    key_id=key_id,
                    units=units,
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    created_at=created_at,
                )
                if prev_units == 0 and effective > 0:
                    inserted_units += effective
                    new_usages.append(
                        _usage_notice(model_name, prompt_tokens, completion_tokens, effective)
                    )
                continue

            if not _insert_usage(
                user_id,
                key_id,
                log_id,
                model_name,
                prompt_tokens,
                completion_tokens,
                units,
                created_at,
                conn,
            ):
                owner = conn.execute(
                    "SELECT user_id FROM usage WHERE upstream_log_id = %s",
                    (log_id,),
                ).fetchone()
                if owner is not None and int(owner["user_id"]) != user_id:
                    log.warning(
                        "расход upstream_log_id=%s уже у user=%s, пропуск user=%s",
                        log_id,
                        owner["user_id"],
                        user_id,
                    )
                    continue
                prev = conn.execute(
                    """
                    SELECT id, quota_units
                    FROM usage
                    WHERE user_id = %s AND upstream_log_id = %s
                    """,
                    (user_id, log_id),
                ).fetchone()
                if prev is None:
                    log.warning(
                        "расход upstream_log_id=%s не записан для user=%s",
                        log_id,
                        user_id,
                    )
                    continue
                prev_units = int(prev["quota_units"] or 0)
                effective = _patch_usage_row(
                    conn,
                    row_id=int(prev["id"]),
                    key_id=key_id,
                    units=units,
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    created_at=created_at,
                )
                if prev_units == 0 and effective > 0:
                    inserted_units += effective
                    new_usages.append(
                        _usage_notice(model_name, prompt_tokens, completion_tokens, effective)
                    )
                continue

            if units > 0:
                inserted_units += units
                new_usages.append(
                    _usage_notice(model_name, prompt_tokens, completion_tokens, units)
                )

    page_done = len(parsed) > 0 and inserted_units == 0 and not new_usages
    return inserted_units, page_done, new_usages


def _warn_if_usage_differs(user_id: int, token: dict) -> None:
    raw_used = token.get("used_quota")
    if raw_used in (None, ""):
        return
    try:
        official = int(raw_used)
    except (TypeError, ValueError):
        return
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(quota_units), 0) AS units FROM usage WHERE user_id = %s",
            (user_id,),
        ).fetchone()
    logged = int(row["units"] or 0)
    if logged != official:
        log.warning(
            "расход пользователя %s не совпал с router.cheap: журнал %s, used_quota %s",
            user_id,
            logged,
            official,
        )


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
) -> bool:
    sql = """
        INSERT INTO usage (
            user_id, api_key_id, upstream_log_id, model_name,
            prompt_tokens, completion_tokens, quota_units, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    if upstream_log_id is not None:
        sql += " ON CONFLICT (upstream_log_id) WHERE upstream_log_id IS NOT NULL DO NOTHING RETURNING id"
    else:
        sql += " RETURNING id"
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
            row = own.execute(sql, params).fetchone()
    else:
        row = conn.execute(sql, params).fetchone()
    return row is not None


def _reraise(exc: UpstreamError) -> None:
    text = exc.message.lower()
    if "не хватает" in text:
        raise BillingError("supplier") from exc
    if "не задан" in text:
        raise BillingError("supplier") from exc
    raise BillingError("upstream") from exc
