import hashlib
import logging
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.db import pool
from app.money import usd_to_units, units_to_usd
from app.upstream import UpstreamError, _log_quota_units, upstream

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
    from app.notifications import check_low_balance_users

    check_low_balance_users()


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


def block_user(user_id: int, reason: str = "") -> None:
    with billing_lock:
        if not _user_exists(user_id):
            raise BillingError("user")
        if _is_blocked(user_id):
            return
        sync_user(user_id)
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
        stats = _key_stats(int(key["id"]), upstream_id, amount) if key else {}
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
        stats = _key_stats(int(key["id"]), new_id, amount) if key else {}
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
        stats = _key_stats(int(key["id"]), upstream_id, quota)
        return {
            "secret": secret,
            "prefix": key["prefix"],
            "base_url": _base_url(),
            "balance_usd": float(_balance(user_id)),
            "created_at": created_at.isoformat() if created_at is not None else "",
            **stats,
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
        user_id, key_id, upstream_id, token_name, token_secret=token_secret
    )
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

    process_new_usages(user_id, telegram_id, key_id, new_usages, amount)
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


def _key_stats(key_id: int, upstream_id: int | None, quota_usd: Decimal) -> dict:
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
        row = conn.execute(
            """
            SELECT COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                   COALESCE(SUM(quota_units), 0) AS spent_units,
                   MAX(created_at) AS last_request_at
            FROM usage
            WHERE api_key_id = %s
            """,
            (key_id,),
        ).fetchone()
        period = conn.execute(
            """
            SELECT
                COALESCE(SUM(quota_units) FILTER (
                    WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'Europe/Moscow')
                        AT TIME ZONE 'Europe/Moscow'
                ), 0) AS today_units,
                COALESCE(SUM(quota_units) FILTER (
                    WHERE created_at >= date_trunc('month', NOW() AT TIME ZONE 'Europe/Moscow')
                        AT TIME ZONE 'Europe/Moscow'
                ), 0) AS month_units
            FROM usage
            WHERE api_key_id = %s
              AND created_at >= date_trunc('month', NOW() AT TIME ZONE 'Europe/Moscow')
                  AT TIME ZONE 'Europe/Moscow'
            """,
            (key_id,),
        ).fetchone()
        week_rows = conn.execute(
            """
            SELECT (created_at AT TIME ZONE 'Europe/Moscow')::date AS day,
                   COALESCE(SUM(quota_units), 0) AS units
            FROM usage
            WHERE api_key_id = %s
              AND (created_at AT TIME ZONE 'Europe/Moscow')::date >= %s
            GROUP BY day
            ORDER BY day
            """,
            (key_id, _week_start_msk()),
        ).fetchall()
    spent_logs = units_to_usd(int(row["spent_units"] or 0))
    if spent_logs > used:
        used = spent_logs
    limit = (remain + used).quantize(Decimal("0.01"))
    last = row["last_request_at"]
    return {
        "quota_usd": float(remain),
        "spent_usd": float(used),
        "limit_usd": float(limit),
        "prompt_tokens": int(row["prompt_tokens"] or 0),
        "completion_tokens": int(row["completion_tokens"] or 0),
        "last_request_at": last.isoformat() if last is not None else "",
        "spent_today_usd": float(units_to_usd(int(period["today_units"] or 0))),
        "spent_month_usd": float(units_to_usd(int(period["month_units"] or 0))),
        "spent_week_usd": _week_chart_rows(week_rows),
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
) -> tuple[Decimal, list[dict]]:
    if key_id is None or (not token_secret and not token_name):
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
    except UpstreamError as exc:
        log.warning("журнал расходов router.cheap не прочитан: %s", exc.message)
    return units_to_usd(inserted_units), new_usages


_WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def _week_start_msk() -> date:
    from zoneinfo import ZoneInfo

    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    return today - timedelta(days=6)


def _week_chart_rows(rows: list[dict]) -> list[dict]:
    from zoneinfo import ZoneInfo

    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    start = today - timedelta(days=6)
    by_day = {row["day"]: float(units_to_usd(int(row["units"] or 0))) for row in rows}
    return [
        {
            "date": day.isoformat(),
            "label": _WEEKDAY_LABELS[day.weekday()],
            "usd": by_day.get(day, 0.0),
        }
        for day in (start + timedelta(days=offset) for offset in range(7))
    ]


def _upstream_log_id(item: dict) -> int | None:
    raw = item.get("id")
    if raw not in (None, ""):
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    created = item.get("created_at")
    model = str(item.get("model_name") or "")
    quota = _log_quota_units(item)
    try:
        prompt = int(item.get("prompt_tokens") or 0)
    except (TypeError, ValueError):
        prompt = 0
    try:
        completion = int(item.get("completion_tokens") or 0)
    except (TypeError, ValueError):
        completion = 0
    if created in (None, "") and not model and quota <= 0:
        return None
    digest = hashlib.sha256(
        f"{created}|{model}|{quota}|{prompt}|{completion}".encode()
    ).hexdigest()
    return int(digest[:15], 16)


def _save_usage_page(user_id: int, key_id: int, items: list[dict]) -> tuple[int, bool, list[dict]]:
    parsed: list[tuple[int, dict]] = []
    for item in items:
        log_id = _upstream_log_id(item)
        if log_id is not None:
            parsed.append((log_id, item))
    if not parsed:
        return 0, True, []
    ids = [log_id for log_id, _ in parsed]
    with pool.connection() as conn:
        known = {
            int(row["upstream_log_id"])
            for row in conn.execute(
                "SELECT upstream_log_id FROM usage WHERE upstream_log_id = ANY(%s)",
                (ids,),
            ).fetchall()
        }
        inserted_units = 0
        new_usages: list[dict] = []
        for log_id, item in parsed:
            units = _log_quota_units(item)
            model_name = str(item.get("model_name") or "")
            try:
                prompt_tokens = int(item.get("prompt_tokens") or 0)
            except (TypeError, ValueError):
                prompt_tokens = 0
            try:
                completion_tokens = int(item.get("completion_tokens") or 0)
            except (TypeError, ValueError):
                completion_tokens = 0
            created_at = _log_time(item.get("created_at"))
            if log_id in known:
                if units > 0:
                    patched = conn.execute(
                        """
                        UPDATE usage
                        SET quota_units = %s,
                            model_name = CASE WHEN model_name = '' THEN %s ELSE model_name END,
                            prompt_tokens = CASE WHEN prompt_tokens = 0 THEN %s ELSE prompt_tokens END,
                            completion_tokens = CASE WHEN completion_tokens = 0 THEN %s ELSE completion_tokens END
                        WHERE upstream_log_id = %s AND quota_units = 0
                        RETURNING id
                        """,
                        (
                            units,
                            model_name[:200],
                            max(prompt_tokens, 0),
                            max(completion_tokens, 0),
                            log_id,
                        ),
                    ).fetchone()
                    if patched is not None:
                        inserted_units += units
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
                continue
            inserted_units += units
            new_usages.append(
                {
                    "model_name": model_name,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "amount_usd": float(units_to_usd(units)),
                }
            )
    page_done = len(parsed) > 0 and inserted_units == 0
    return inserted_units, page_done, new_usages


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
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if text:
            if text.isdigit():
                value = int(text)
            else:
                try:
                    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
                except ValueError:
                    moment = None
                if moment is not None:
                    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)
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
