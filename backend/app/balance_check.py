"""Сверка балансов клиентов с ключами router.cheap для админки.

Новая логика: клиент видит API-$, а у поставщика ключ выставлен в реальных $:
remain_quota = баланс клиента / курс ключа. Здесь по каждому ключу проверяем,
что это действительно так, и что поставщик списывает ключ в тех же единицах,
что пишет в журнал запросов.
"""

import logging
from decimal import Decimal

from app.db import pool
from app.money import (
    api_usd_to_real_units,
    key_rate,
    real_units_to_api_usd,
    supplier_api_usd_rate,
    units_to_usd,
)
from app.upstream import UpstreamError, upstream

log = logging.getLogger("app.balance_check")

# Допуск сверки баланса: расход между синхронизациями и округление до единиц квоты.
BALANCE_TOLERANCE_USD = Decimal("0.01")
# Допуск сверки «списано с ключа» vs «сумма журнала» (в долях).
USAGE_TOLERANCE = Decimal("0.02")


def _person(row: dict) -> str:
    name = str(row.get("first_name") or "").strip()
    if row.get("username"):
        handle = f"@{row['username']}"
    elif row.get("telegram_id"):
        handle = str(row["telegram_id"])
    else:
        handle = str(row.get("email") or "").strip() or "сайт"
    return f"{name} {handle}".strip()


def _f(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def balance_report() -> dict:
    rate = supplier_api_usd_rate()
    with pool.connection() as conn:
        keys = conn.execute(
            """
            SELECT k.id AS key_id, k.user_id, k.upstream_id, k.prefix, k.quota_rate,
                   k.frozen_at, k.created_at AS key_created_at,
                   u.balance_usd, u.username, u.first_name, u.email, u.telegram_id, u.blocked_at,
                   COALESCE(s.units, 0) AS log_units,
                   COALESCE(s.real_units, 0) AS log_real_units,
                   COALESCE(s.requests, 0) AS requests,
                   s.last_at,
                   l.quota_units AS last_units,
                   l.real_units AS last_real_units
            FROM api_keys k
            JOIN users u ON u.id = k.user_id
            LEFT JOIN LATERAL (
                SELECT SUM(quota_units) AS units, SUM(real_units) AS real_units,
                       COUNT(*) AS requests, MAX(created_at) AS last_at
                FROM usage WHERE api_key_id = k.id
            ) s ON TRUE
            LEFT JOIN LATERAL (
                SELECT quota_units, real_units
                FROM usage
                WHERE api_key_id = k.id AND real_units > 0
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            ) l ON TRUE
            WHERE k.revoked_at IS NULL AND k.upstream_id IS NOT NULL
            ORDER BY u.balance_usd DESC, k.id
            """
        ).fetchall()
        keyless = conn.execute(
            """
            SELECT u.id, u.username, u.first_name, u.email, u.telegram_id, u.balance_usd
            FROM users u
            WHERE u.balance_usd <> 0
              AND NOT EXISTS (
                  SELECT 1 FROM api_keys k
                  WHERE k.user_id = u.id AND k.revoked_at IS NULL AND k.upstream_id IS NOT NULL
              )
            ORDER BY u.balance_usd DESC
            """
        ).fetchall()

    items: list[dict] = []
    totals = {
        "local_usd": Decimal(0),
        "active_local_usd": Decimal(0),
        "frozen_local_usd": Decimal(0),
        "keyless_local_usd": Decimal(0),
        "keys_real_usd": Decimal(0),
        "keys_api_usd": Decimal(0),
    }
    counts = {"ok": 0, "warn": 0, "bad": 0}

    for row in keys:
        local = Decimal(row["balance_usd"] or 0)
        frozen = row["frozen_at"] is not None
        stored_rate = row["quota_rate"]
        k_rate = key_rate(stored_rate)
        totals["local_usd"] += local
        totals["frozen_local_usd" if frozen else "active_local_usd"] += local

        checks: list[dict] = []
        token = None
        error = ""
        try:
            token = upstream.get_token(int(row["upstream_id"]))
        except UpstreamError as exc:
            error = exc.message
        except Exception as exc:  # отчёт не должен падать из-за одного ключа
            log.exception("сверка ключа %s", row["upstream_id"])
            error = str(exc)

        remain_units = used_units = None
        remain_real = remain_api = used_real = None
        wallet = None
        enabled = None
        expected_units = None
        diff_api = None
        if token is not None:
            remain_units = int(token.get("remain_quota") or 0)
            used_units = int(token.get("used_quota") or 0)
            remain_real = units_to_usd(remain_units)
            remain_api = real_units_to_api_usd(remain_units, k_rate)
            used_real = units_to_usd(used_units)
            wallet = bool(token.get("limit_by_wallet_charge"))
            try:
                enabled = int(token.get("status") or 1) == 1
            except (TypeError, ValueError):
                enabled = None
            totals["keys_real_usd"] += remain_real
            totals["keys_api_usd"] += remain_api

        # 1. Курс ключа = курс из админки.
        if stored_rate is None:
            checks.append({
                "tone": "warn",
                "text": "Старый ключ 1:1 — ещё не переведён на курс (сделает ближайшая синхронизация)",
            })
        elif Decimal(stored_rate) != rate:
            checks.append({
                "tone": "warn",
                "text": f"Ключ выставлен по курсу {Decimal(stored_rate).normalize()}, "
                        f"в админке {rate.normalize()} — ждёт пересчёта",
            })

        if error:
            checks.append({"tone": "bad", "text": f"router.cheap не ответил: {error}"})
        elif token is None:
            checks.append({"tone": "bad", "text": "Ключ не найден у router.cheap"})
        else:
            # 2. Списание по балансу кабинета (реальные $).
            if not wallet:
                checks.append({"tone": "bad", "text": "Выключено «Считать лимит по списанию с баланса»"})
            # 3. Баланс клиента = остаток ключа × курс.
            if frozen:
                expected_units = 0
                if remain_units > 0:
                    checks.append({
                        "tone": "bad",
                        "text": "Ключ заморожен, но у поставщика осталась квота",
                    })
            else:
                expected_units = api_usd_to_real_units(max(local, Decimal(0)), k_rate)
                diff_api = (local - remain_api).quantize(Decimal("0.0001"))
                if diff_api > BALANCE_TOLERANCE_USD:
                    checks.append({
                        "tone": "warn",
                        "text": f"Баланс в сервисе больше остатка ключа на ${diff_api} — "
                                "есть ещё не подтянутые запросы, нажмите «Синхронизировать»",
                    })
                elif diff_api < -BALANCE_TOLERANCE_USD:
                    checks.append({
                        "tone": "bad",
                        "text": f"У ключа на ${-diff_api} больше, чем баланс клиента",
                    })
            # 4. Поставщик списывает ключ в тех же единицах, что пишет журнал.
            log_real = int(row["log_real_units"] or 0)
            if used_units and log_real:
                gap = Decimal(abs(used_units - log_real)) / Decimal(max(used_units, log_real))
                if gap > USAGE_TOLERANCE:
                    checks.append({
                        "tone": "warn",
                        "text": f"Списано с ключа ${used_real}, а в журнале ${units_to_usd(log_real)} "
                                "(реальных $) — журнал неполный или единицы не совпадают",
                    })

        tone = "ok"
        if any(c["tone"] == "bad" for c in checks):
            tone = "bad"
        elif checks:
            tone = "warn"
        counts[tone] += 1

        last_units = row["last_units"]
        last_real = row["last_real_units"]
        last_rate = None
        if last_units and last_real:
            last_rate = (Decimal(int(last_units)) / Decimal(int(last_real))).quantize(Decimal("0.0001"))

        items.append({
            "user_id": row["user_id"],
            "person": _person(row),
            "key_id": row["key_id"],
            "upstream_id": row["upstream_id"],
            "prefix": row["prefix"] or "",
            "frozen": frozen,
            "blocked": row["blocked_at"] is not None,
            "enabled": enabled,
            "key_rate": _f(Decimal(stored_rate)) if stored_rate is not None else None,
            "local_usd": float(local),
            "remain_units": remain_units,
            "expected_units": expected_units,
            "remain_real_usd": _f(remain_real),
            "remain_api_usd": _f(remain_api),
            "diff_usd": _f(diff_api),
            "used_real_usd": _f(used_real),
            "wallet_charge": wallet,
            "log_api_usd": float(units_to_usd(int(row["log_units"] or 0))),
            "log_real_usd": float(units_to_usd(int(row["log_real_units"] or 0))),
            "requests": int(row["requests"] or 0),
            "last_request_at": row["last_at"].isoformat() if row["last_at"] is not None else "",
            "last_request_rate": _f(last_rate),
            "tone": tone,
            "checks": checks,
        })

    keyless_items = []
    for row in keyless:
        amount = Decimal(row["balance_usd"] or 0)
        totals["keyless_local_usd"] += amount
        totals["local_usd"] += amount
        keyless_items.append({
            "user_id": row["id"],
            "person": _person(row),
            "local_usd": float(amount),
        })

    cabinet_real = cabinet_error = None
    try:
        cabinet_real = upstream.supplier_balance_real_usd()
    except UpstreamError as exc:
        cabinet_error = exc.message
    except Exception as exc:
        cabinet_error = str(exc)

    # Обязательства перед всеми клиентами в реальных $ кабинета.
    need_real = (totals["local_usd"] / rate).quantize(Decimal("0.0001")) if rate > 0 else Decimal(0)
    coverage = None if cabinet_real is None else (cabinet_real - need_real).quantize(Decimal("0.0001"))

    return {
        "rate": float(rate),
        "tolerance_usd": float(BALANCE_TOLERANCE_USD),
        "totals": {key: float(value.quantize(Decimal("0.0001"))) for key, value in totals.items()},
        "need_real_usd": float(need_real),
        "cabinet_real_usd": _f(cabinet_real),
        "cabinet_api_usd": _f((cabinet_real * rate).quantize(Decimal("0.0001")) if cabinet_real is not None else None),
        "cabinet_error": cabinet_error or "",
        "coverage_real_usd": _f(coverage),
        "counts": counts,
        "items": items,
        "keyless": keyless_items,
    }
