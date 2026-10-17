"""Письма пользователям сайта: ключ доступа и ссылка в кабинет после оплаты.

SMTP задаётся в .env. Отправка идёт в фоновом потоке, чтобы не задерживать вебхук ЮKassa.
Каждая попытка пишется в outbound_emails (без тела письма). Повтор — только вручную из админки,
с пересборкой письма и новым login-токеном.
Ссылка для входа — одноразовый токен на пользователе (users.email_login_hash), как return_url у ЮKassa.
"""

import html
import json
import logging
import secrets
import smtplib
import ssl
import threading
from decimal import Decimal
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

from app.config import settings
from app.db import pool
from app.settings_store import get_setting, public_base_url, support_username
from app.web_auth import key_hash

log = logging.getLogger("app.mailer")

KIND_LOGIN = "login"
KIND_LOGIN_WELCOME = "login_welcome"
KIND_PAYMENT = "payment"
KIND_PAYMENT_DELAYED = "payment_delayed"
KIND_SUPPORT_REPLY = "support_reply"
KIND_NUDGE_TOPUP = "nudge_topup"

KIND_LABELS = {
    KIND_LOGIN: "Вход в кабинет",
    KIND_LOGIN_WELCOME: "Аккаунт создан",
    KIND_PAYMENT: "Оплата / ключ",
    KIND_PAYMENT_DELAYED: "Оплата (ожидание ключа)",
    KIND_SUPPORT_REPLY: "Ответ поддержки",
    KIND_NUDGE_TOPUP: "Напоминание о пополнении",
}

_ERROR_MAX = 500


class MailerError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.smtp_host.strip() and (settings.smtp_from.strip() or settings.smtp_user.strip()))


def issue_email_login_token(user_id: int) -> str:
    """Новый токен для входа по ссылке из письма. Старый перестаёт действовать."""
    token = secrets.token_urlsafe(24)
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET email_login_hash = %s,
                email_login_expires_at = NOW() + make_interval(days => %s)
            WHERE id = %s
            """,
            (key_hash(token), max(1, settings.email_login_ttl_days), user_id),
        )
    return token


def login_link(token: str) -> str:
    return f"{public_base_url()}/login?t={token}"


def _money_ctx(**values: Decimal | bool | str | int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Decimal):
            out[key] = format(value, "f")
        else:
            out[key] = value
    return out


def _create_outbound(
    *,
    user_id: int | None,
    kind: str,
    to_email: str,
    subject: str,
    context: dict[str, Any] | None = None,
) -> int:
    with pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO outbound_emails (user_id, kind, to_email, subject, context)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            RETURNING id
            """,
            (user_id, kind, to_email, subject, json.dumps(context or {}, ensure_ascii=False)),
        ).fetchone()
    return int(row["id"])


def _mark_outbound(email_id: int, *, ok: bool, error: str = "") -> None:
    err = (error or "").strip()[:_ERROR_MAX]
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE outbound_emails
            SET attempts = attempts + 1,
                status = %s,
                last_error = %s,
                sent_at = CASE WHEN %s THEN NOW() ELSE sent_at END,
                updated_at = NOW()
            WHERE id = %s
            """,
            ("sent" if ok else "failed", "" if ok else err, ok, email_id),
        )


def _outbound_status(email_id: int) -> str:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT status FROM outbound_emails WHERE id = %s",
            (email_id,),
        ).fetchone()
    return str(row["status"]) if row else "failed"


def _dispatch(
    *,
    user_id: int | None,
    kind: str,
    to_email: str,
    subject: str,
    text: str,
    body_html: str,
    context: dict[str, Any] | None = None,
    sync: bool = False,
) -> int:
    """Создаёт запись журнала и отправляет (sync или фон). Тело письма в БД не пишется."""
    email_id = _create_outbound(
        user_id=user_id,
        kind=kind,
        to_email=to_email,
        subject=subject,
        context=context,
    )
    if not enabled():
        _mark_outbound(email_id, ok=False, error="SMTP не настроен")
        log.info("SMTP не настроен — письмо %s (%s) не отправлено", kind, email_id)
        return email_id
    if sync:
        _attempt_send(email_id, to_email, subject, text, body_html)
    else:
        threading.Thread(
            target=_attempt_send,
            args=(email_id, to_email, subject, text, body_html),
            name=f"mail-{email_id}",
            daemon=True,
        ).start()
    return email_id


def _attempt_send(
    email_id: int,
    to_email: str,
    subject: str,
    text: str,
    body_html: str,
) -> bool:
    try:
        send_mail(to_email, subject, text, body_html)
        _mark_outbound(email_id, ok=True)
        log.info("письмо «%s» #%s отправлено на %s", subject, email_id, to_email)
        return True
    except Exception as exc:
        _mark_outbound(email_id, ok=False, error=str(exc))
        log.exception(
            "не удалось отправить письмо #%s на %s через %s:%s (%s)",
            email_id,
            to_email,
            settings.smtp_host.strip(),
            settings.smtp_port,
            settings.smtp_security.strip().lower() or "starttls",
        )
        return False


def _user_email(user_id: int) -> str | None:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT email FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    if row is None or not (row["email"] or "").strip():
        return None
    return str(row["email"]).strip()


def _build_login_message(user_id: int, *, created: bool) -> tuple[str, str, str, str]:
    email = _user_email(user_id)
    if not email:
        raise MailerError("у пользователя нет email")
    token = issue_email_login_token(user_id)
    link = login_link(token)
    support = _support_line()
    if created:
        subject = "Вход в Aimarket — ваш аккаунт создан"
        intro = "Аккаунт Aimarket создан. Войдите по кнопке ниже — ключ появится после первого пополнения."
    else:
        subject = "Вход в личный кабинет Aimarket"
        intro = "Запрошен вход в личный кабинет Aimarket. Нажмите кнопку ниже — ссылка одноразовая."
    text = (
        f"{intro}\n\n"
        f"Войти (действует {settings.email_login_ttl_days} дн.):\n{link}\n\n"
        f"{support}\n"
    )
    body_html = f"""<!DOCTYPE html>
<html lang="ru"><body style="margin:0;padding:0;background:#f4f1ea;font:16px/1.55 'Segoe UI',system-ui,sans-serif;color:#1c1915">
  <div style="max-width:560px;margin:0 auto;padding:32px 20px">
    <p style="margin:0 0 16px;font-weight:700;letter-spacing:-0.03em;font-size:18px">Aimarket</p>
    <div style="background:#fff;border:1px solid rgba(28,25,21,.08);border-radius:16px;padding:24px">
      <h1 style="margin:0 0 12px;font-size:22px;letter-spacing:-0.03em">{html.escape(intro)}</h1>
      <p style="margin:0;color:#4f473d;font-size:15px;line-height:1.5">
        Если вы не запрашивали вход — просто проигнорируйте это письмо.
      </p>
      <p style="margin:24px 0 0;text-align:center">
        <a href="{html.escape(link)}" style="display:inline-block;padding:14px 26px;border-radius:999px;background:#1c1915;
           color:#f4f1ea;font-weight:600;text-decoration:none">Войти в личный кабинет</a>
      </p>
      <p style="margin:12px 0 0;text-align:center;color:#6b645b;font-size:13px">
        Кнопка работает {settings.email_login_ttl_days} дн.<br>
        Если не открывается, скопируйте ссылку: <span style="word-break:break-all">{html.escape(link)}</span>
      </p>
    </div>
    <p style="margin:18px 0 0;color:#6b645b;font-size:13px;text-align:center">{html.escape(support)}</p>
  </div>
</body></html>"""
    return email, subject, text, body_html


def _record_smtp_disabled(
    *,
    user_id: int | None,
    kind: str,
    to_email: str,
    subject: str,
    context: dict[str, Any] | None = None,
) -> int:
    email_id = _create_outbound(
        user_id=user_id,
        kind=kind,
        to_email=to_email,
        subject=subject,
        context=context,
    )
    _mark_outbound(email_id, ok=False, error="SMTP не настроен")
    log.info("SMTP не настроен — письмо %s (%s) не отправлено", kind, email_id)
    return email_id


def send_login_email(user_id: int, *, created: bool = False) -> bool:
    """Письмо со ссылкой входа в кабинет (для существующих и новых аккаунтов по почте)."""
    email = _user_email(user_id)
    if not email:
        return False
    kind = KIND_LOGIN_WELCOME if created else KIND_LOGIN
    subject = (
        "Вход в Aimarket — ваш аккаунт создан"
        if created
        else "Вход в личный кабинет Aimarket"
    )
    context = {"created": created}
    if not enabled():
        _record_smtp_disabled(
            user_id=user_id, kind=kind, to_email=email, subject=subject, context=context
        )
        return False
    try:
        email, subject, text, body_html = _build_login_message(user_id, created=created)
    except MailerError:
        return False
    # Welcome при создании — синхронно: иначе checkout/login думают, что письмо ушло.
    email_id = _dispatch(
        user_id=user_id,
        kind=kind,
        to_email=email,
        subject=subject,
        text=text,
        body_html=body_html,
        context=context,
        sync=created,
    )
    if created:
        return _outbound_status(email_id) == "sent"
    return True


def _build_payment_delayed_message(
    user_id: int,
    *,
    amount_usd: Decimal,
    bonus_usd: Decimal,
) -> tuple[str, str, str, str]:
    email = _user_email(user_id)
    if not email:
        raise MailerError("у пользователя нет email")
    token = issue_email_login_token(user_id)
    link = login_link(token)
    support = _support_line()
    amount = f"${amount_usd:.2f}"
    bonus_line = f" + бонус ${bonus_usd:.2f}" if bonus_usd > 0 else ""
    intro = "Оплата получена — личный кабинет уже доступен."
    subject = "Оплата Aimarket — войдите в кабинет"
    text = (
        f"{intro}\n\n"
        f"Сумма: {amount}{bonus_line}\n\n"
        "Ключ доступа пока не выпущен — не хватает лимита у поставщика API. "
        "Зайдите в кабинет по ссылке ниже и напишите в поддержку — мы зачислим баланс и выпустим ключ.\n\n"
        f"Войти (действует {settings.email_login_ttl_days} дн.):\n{link}\n\n"
        f"{support}\n"
    )
    body_html = f"""<!DOCTYPE html>
<html lang="ru"><body style="margin:0;padding:0;background:#f4f1ea;font:16px/1.55 'Segoe UI',system-ui,sans-serif;color:#1c1915">
  <div style="max-width:560px;margin:0 auto;padding:32px 20px">
    <p style="margin:0 0 16px;font-weight:700;letter-spacing:-0.03em;font-size:18px">Aimarket</p>
    <div style="background:#fff;border:1px solid rgba(28,25,21,.08);border-radius:16px;padding:24px">
      <h1 style="margin:0 0 12px;font-size:22px;letter-spacing:-0.03em">{html.escape(intro)}</h1>
      <p style="margin:0 0 12px;color:#4f473d;font-size:15px;line-height:1.5">
        Сумма: <b>{amount}{html.escape(bonus_line)}</b>
      </p>
      <p style="margin:0;padding:12px 14px;border:1px solid #ecdca8;border-radius:10px;background:#faf3dd;
                color:#5c4300;font-size:14px;line-height:1.5">
        Ключ доступа пока не выпущен — временная проблема с поставщиком API.
        Войдите в кабинет и напишите в поддержку: мы зачислим баланс и выпустим ключ.
      </p>
      <p style="margin:24px 0 0;text-align:center">
        <a href="{html.escape(link)}" style="display:inline-block;padding:14px 26px;border-radius:999px;background:#1c1915;
           color:#f4f1ea;font-weight:600;text-decoration:none">Войти в личный кабинет</a>
      </p>
      <p style="margin:12px 0 0;text-align:center;color:#6b645b;font-size:13px">
        Кнопка работает {settings.email_login_ttl_days} дн.<br>
        Если не открывается, скопируйте ссылку: <span style="word-break:break-all">{html.escape(link)}</span>
      </p>
    </div>
    <p style="margin:18px 0 0;color:#6b645b;font-size:13px;text-align:center">{html.escape(support)}</p>
  </div>
</body></html>"""
    return email, subject, text, body_html


def send_payment_delayed_email(
    user_id: int,
    *,
    amount_usd: Decimal,
    bonus_usd: Decimal,
) -> bool:
    """Оплата в ЮKassa прошла, но ключ ещё не выпущен — даём вход в кабинет по ссылке."""
    email = _user_email(user_id)
    if not email:
        return False
    subject = "Оплата Aimarket — войдите в кабинет"
    context = _money_ctx(amount_usd=amount_usd, bonus_usd=bonus_usd)
    if not enabled():
        _record_smtp_disabled(
            user_id=user_id,
            kind=KIND_PAYMENT_DELAYED,
            to_email=email,
            subject=subject,
            context=context,
        )
        return False
    try:
        email, subject, text, body_html = _build_payment_delayed_message(
            user_id, amount_usd=amount_usd, bonus_usd=bonus_usd
        )
    except MailerError:
        return False
    _dispatch(
        user_id=user_id,
        kind=KIND_PAYMENT_DELAYED,
        to_email=email,
        subject=subject,
        text=text,
        body_html=body_html,
        context=context,
    )
    return True


def _build_payment_message_for_user(
    user_id: int,
    *,
    amount_usd: Decimal,
    bonus_usd: Decimal,
    balance_usd: Decimal,
    first_key: bool,
) -> tuple[str, str, str, str]:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT u.email, k.secret
            FROM users u
            LEFT JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL AND k.upstream_id IS NOT NULL
            WHERE u.id = %s
            """,
            (user_id,),
        ).fetchone()
    if row is None or not (row["email"] or "").strip():
        raise MailerError("у пользователя нет email")
    email = str(row["email"]).strip()
    secret = str(row["secret"] or "")
    token = issue_email_login_token(user_id)
    link = login_link(token)
    base_url = settings.router_base_url.rstrip("/") + "/v1"
    subject = "Ваш ключ доступа Aimarket" if first_key else "Баланс Aimarket пополнен"
    text, body_html = _payment_message(
        amount_usd=amount_usd,
        bonus_usd=bonus_usd,
        balance_usd=balance_usd,
        secret=secret,
        link=link,
        base_url=base_url,
        first_key=first_key,
    )
    return email, subject, text, body_html


def send_payment_email(
    user_id: int,
    *,
    amount_usd: Decimal,
    bonus_usd: Decimal,
    balance_usd: Decimal,
    first_key: bool,
) -> None:
    email = _user_email(user_id)
    if not email:
        return
    subject = "Ваш ключ доступа Aimarket" if first_key else "Баланс Aimarket пополнен"
    context = _money_ctx(
        amount_usd=amount_usd,
        bonus_usd=bonus_usd,
        balance_usd=balance_usd,
        first_key=first_key,
    )
    if not enabled():
        _record_smtp_disabled(
            user_id=user_id,
            kind=KIND_PAYMENT,
            to_email=email,
            subject=subject,
            context=context,
        )
        return
    try:
        email, subject, text, body_html = _build_payment_message_for_user(
            user_id,
            amount_usd=amount_usd,
            bonus_usd=bonus_usd,
            balance_usd=balance_usd,
            first_key=first_key,
        )
    except MailerError:
        return
    _dispatch(
        user_id=user_id,
        kind=KIND_PAYMENT,
        to_email=email,
        subject=subject,
        text=text,
        body_html=body_html,
        context=context,
    )


def _payment_message(
    *,
    amount_usd: Decimal,
    bonus_usd: Decimal,
    balance_usd: Decimal,
    secret: str,
    link: str,
    base_url: str,
    first_key: bool,
) -> tuple[str, str]:
    support = _support_line()
    amount = f"${amount_usd:.2f}"
    bonus_line = f" + бонус ${bonus_usd:.2f}" if bonus_usd > 0 else ""
    balance = f"${balance_usd:.2f}"
    intro = (
        "Спасибо за оплату! Ваш аккаунт Aimarket готов."
        if first_key
        else "Платёж получен, баланс пополнен."
    )
    key_block_text = (
        f"\nВаш ключ доступа:\n{secret}\n\n"
        "Этот ключ — и пароль для входа в личный кабинет, и API-ключ для нейросетей.\n"
        f"Адрес сервера (Base URL) для приложений: {base_url}\n"
        "Сохраните ключ в надёжном месте и никому не передавайте.\n"
        "Пошаговая инструкция и установщики для Cursor, Codex, Claude Code и других — "
        "в разделе «Подключение» личного кабинета.\n"
        if secret
        else "\nКлюч доступа появится в личном кабинете через минуту.\n"
    )
    text = (
        f"{intro}\n\n"
        f"Зачислено: {amount}{bonus_line}\n"
        f"Баланс: {balance}\n"
        f"{key_block_text}\n"
        f"Войти в личный кабинет (ссылка действует {settings.email_login_ttl_days} дн.):\n{link}\n\n"
        f"{support}\n"
    )

    key_block_html = (
        f"""
        <p style="margin:24px 0 8px;font-weight:600">Ваш ключ доступа</p>
        <div style="padding:14px 16px;border:1px solid #d9d0c3;border-radius:10px;background:#faf7f2;
                    font:600 15px/1.4 ui-monospace,Consolas,monospace;word-break:break-all">{html.escape(secret)}</div>
        <p style="margin:12px 0 0;color:#4f473d;font-size:14px;line-height:1.5">
          Этот ключ — <b>и пароль для входа в личный кабинет, и API-ключ для нейросетей</b>.
          Укажите его в Cursor, Codex, Claude Code или другом приложении как API key, а адресом сервера
          (Base URL) поставьте <code style="background:#faf7f2;padding:1px 6px;border-radius:6px">{html.escape(base_url)}</code>.
          Пошаговая инструкция и готовые установщики — в разделе «Подключение» личного кабинета.
        </p>
        <p style="margin:12px 0 0;padding:12px 14px;border:1px solid #ecdca8;border-radius:10px;background:#faf3dd;
                  color:#5c4300;font-size:14px;line-height:1.5">
          Сохраните ключ в менеджере паролей. Без него войти в кабинет не получится, а любой, у кого он есть,
          сможет тратить ваш баланс.
        </p>
        """
        if secret
        else '<p style="margin:24px 0 0;color:#4f473d">Ключ доступа появится в личном кабинете через минуту.</p>'
    )
    body_html = f"""<!DOCTYPE html>
<html lang="ru"><body style="margin:0;padding:0;background:#f4f1ea;font:16px/1.55 'Segoe UI',system-ui,sans-serif;color:#1c1915">
  <div style="max-width:560px;margin:0 auto;padding:32px 20px">
    <p style="margin:0 0 16px;font-weight:700;letter-spacing:-0.03em;font-size:18px">Aimarket</p>
    <div style="background:#fff;border:1px solid rgba(28,25,21,.08);border-radius:16px;padding:24px">
      <h1 style="margin:0 0 12px;font-size:22px;letter-spacing:-0.03em">{html.escape(intro)}</h1>
      <table style="border-collapse:collapse;font-size:15px">
        <tr><td style="padding:4px 16px 4px 0;color:#6b645b">Зачислено</td><td style="padding:4px 0;font-weight:600">{amount}{html.escape(bonus_line)}</td></tr>
        <tr><td style="padding:4px 16px 4px 0;color:#6b645b">Баланс</td><td style="padding:4px 0;font-weight:600">{balance}</td></tr>
      </table>
      {key_block_html}
      <p style="margin:24px 0 0;text-align:center">
        <a href="{html.escape(link)}" style="display:inline-block;padding:14px 26px;border-radius:999px;background:#1c1915;
           color:#f4f1ea;font-weight:600;text-decoration:none">Войти в личный кабинет</a>
      </p>
      <p style="margin:12px 0 0;text-align:center;color:#6b645b;font-size:13px">
        Кнопка работает {settings.email_login_ttl_days} дн. и открывает кабинет без ввода ключа.<br>
        Если не открывается, скопируйте ссылку: <span style="word-break:break-all">{html.escape(link)}</span>
      </p>
    </div>
    <p style="margin:18px 0 0;color:#6b645b;font-size:13px;text-align:center">{html.escape(support)}</p>
  </div>
</body></html>"""
    return text, body_html


# Не чаще одного письма о ответе поддержки за этот интервал (антиспам в активном диалоге).
_SUPPORT_MAIL_COOLDOWN_MIN = 20


def _support_preview(body: str, limit: int = 420) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip()
    return (cut or text[: limit - 1]) + "…"


def _build_support_reply_message(user_id: int, *, preview: str) -> tuple[str, str, str, str]:
    email = _user_email(user_id)
    if not email:
        raise MailerError("у пользователя нет email")
    if not preview.strip():
        raise MailerError("пустой текст ответа")
    token = issue_email_login_token(user_id)
    link = f"{login_link(token)}&next=chat"
    support = _support_line()
    subject = "Ответ поддержки Aimarket"
    text, body_html = _support_reply_message(preview=preview, link=link, support=support)
    return email, subject, text, body_html


def maybe_send_support_reply_email(user_id: int, body: str) -> bool:
    """Письмо о новом ответе поддержки: только если включены уведомления и прошла пауза."""
    preview = _support_preview(body)
    if not preview:
        return False
    with pool.connection() as conn:
        row = conn.execute(
            """
            UPDATE users
            SET support_mail_sent_at = NOW()
            WHERE id = %s
              AND notify_support_email
              AND BTRIM(email) <> ''
              AND (
                    support_mail_sent_at IS NULL
                    OR support_mail_sent_at < NOW() - make_interval(mins => %s)
                  )
            RETURNING email
            """,
            (user_id, _SUPPORT_MAIL_COOLDOWN_MIN),
        ).fetchone()
    if row is None:
        return False
    email = str(row["email"]).strip()
    subject = "Ответ поддержки Aimarket"
    context = {"preview": preview}
    if not enabled():
        _record_smtp_disabled(
            user_id=user_id,
            kind=KIND_SUPPORT_REPLY,
            to_email=email,
            subject=subject,
            context=context,
        )
        return False
    try:
        email, subject, text, body_html = _build_support_reply_message(user_id, preview=preview)
    except MailerError:
        return False
    _dispatch(
        user_id=user_id,
        kind=KIND_SUPPORT_REPLY,
        to_email=email,
        subject=subject,
        text=text,
        body_html=body_html,
        context=context,
    )
    return True


def _support_reply_message(*, preview: str, link: str, support: str) -> tuple[str, str]:
    ttl = settings.email_login_ttl_days
    safe_preview = html.escape(preview).replace("\n", "<br>")
    text = (
        "Поддержка ответила в чате Aimarket.\n\n"
        f"{preview}\n\n"
        f"Открыть чат (действует {ttl} дн.):\n{link}\n\n"
        "Отключить письма можно в чате поддержки на сайте.\n\n"
        f"{support}\n"
    )
    # Стили как на сайте: cream bg, белая карточка, «пузырь» ответа поддержки.
    body_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ответ поддержки Aimarket</title>
</head>
<body style="margin:0;padding:0;background:#f4f1ea;font:16px/1.55 'Segoe UI',system-ui,-apple-system,sans-serif;color:#1c1915">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0">
    Поддержка ответила: {html.escape(preview[:120])}
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1ea;border-collapse:collapse">
    <tr>
      <td align="center" style="padding:36px 16px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;border-collapse:collapse">
          <tr>
            <td style="padding:0 4px 18px;font-weight:700;letter-spacing:-0.03em;font-size:20px;color:#1c1915">
              Aimarket
            </td>
          </tr>
          <tr>
            <td style="background:#ffffff;border:1px solid rgba(28,25,21,0.08);border-radius:16px;overflow:hidden;box-shadow:0 14px 30px rgba(28,25,21,0.08)">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
                <tr>
                  <td style="padding:22px 24px 8px">
                    <p style="margin:0 0 6px;font-size:12px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#6b645b">
                      Чат поддержки
                    </p>
                    <h1 style="margin:0;font-size:24px;line-height:1.25;letter-spacing:-0.03em;font-weight:700;color:#1c1915">
                      Вам ответили
                    </h1>
                    <p style="margin:10px 0 0;font-size:15px;line-height:1.5;color:#4f473d">
                      Новое сообщение в переписке на сайте.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 24px 8px">
                    <div style="background:#faf7f2;border:1px solid rgba(28,25,21,0.08);border-radius:14px;padding:16px">
                      <p style="margin:0 0 8px;font-size:12px;font-weight:600;color:#6b645b">Поддержка</p>
                      <div style="display:inline-block;max-width:100%;padding:12px 14px;background:#ffffff;border:1px solid #d9d0c3;border-radius:14px;border-bottom-left-radius:4px;color:#1c1915;font-size:15px;line-height:1.5;text-align:left">
                        {safe_preview}
                      </div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 24px 10px;text-align:center">
                    <a href="{html.escape(link)}"
                       style="display:inline-block;padding:14px 28px;border-radius:999px;background:#1c1915;color:#f4f1ea;font-weight:600;font-size:15px;text-decoration:none;box-shadow:0 14px 30px rgba(28,25,21,0.16)">
                      Открыть чат
                    </a>
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 24px 22px;text-align:center">
                    <p style="margin:0;font-size:13px;line-height:1.5;color:#6b645b">
                      Ссылка действует {ttl} дн. и сразу открывает чат.<br>
                      Если кнопка не работает, скопируйте:<br>
                      <span style="word-break:break-all;color:#4f473d">{html.escape(link)}</span>
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 8px 0;text-align:center;font-size:13px;line-height:1.5;color:#6b645b">
              Письма можно отключить в чате поддержки на сайте.<br>
              {html.escape(support)}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return text, body_html


def _build_nudge_topup_message(user_id: int, email: str | None = None) -> tuple[str, str, str, str]:
    to = (email or "").strip() or _user_email(user_id)
    if not to:
        raise MailerError("у пользователя нет email")
    token = issue_email_login_token(user_id)
    link = f"{login_link(token)}&next=cabinet"
    support = _support_line()
    subject = "Пополните баланс Aimarket"
    text = (
        "Вы создали аккаунт Aimarket, но баланс ещё не пополнен.\n\n"
        "После оплаты вы получите ключ доступа и сможете подключить Cursor, Codex, Claude Code и другие приложения.\n\n"
        f"Открыть кабинет (действует {settings.email_login_ttl_days} дн.):\n{link}\n\n"
        f"{support}\n"
    )
    body_html = _lifecycle_email_html(
        eyebrow="Aimarket",
        title="Баланс ещё пуст",
        lead="Вы зарегистрировались, но пока не пополнили счёт. После оплаты сразу появится ключ для нейросетей.",
        points=(
            "Минимальное пополнение — и ключ в письме и кабинете",
            "Один ключ для Cursor, Codex, Claude Code и других приложений",
            "Оплата через ЮKassa, вход по ссылке из письма",
        ),
        cta="Пополнить баланс",
        link=link,
        support=support,
    )
    return to, subject, text, body_html


def send_nudge_topup_email(user_id: int, email: str) -> bool:
    """Через сутки после регистрации, если ещё не было оплаты."""
    to = (email or "").strip()
    if not to:
        return False
    subject = "Пополните баланс Aimarket"
    if not enabled():
        _record_smtp_disabled(
            user_id=user_id,
            kind=KIND_NUDGE_TOPUP,
            to_email=to,
            subject=subject,
            context={},
        )
        return False
    try:
        to, subject, text, body_html = _build_nudge_topup_message(user_id, to)
    except MailerError:
        return False
    # Синхронно: lifecycle должен знать, ушло ли письмо, иначе отметка «отправлено» ложная.
    email_id = _dispatch(
        user_id=user_id,
        kind=KIND_NUDGE_TOPUP,
        to_email=to,
        subject=subject,
        text=text,
        body_html=body_html,
        context={},
        sync=True,
    )
    return _outbound_status(email_id) == "sent"


def _lifecycle_email_html(
    *,
    eyebrow: str,
    title: str,
    lead: str,
    points: tuple[str, ...],
    cta: str,
    link: str,
    support: str,
) -> str:
    ttl = settings.email_login_ttl_days
    items = "".join(
        f"""
        <tr>
          <td style="padding:0 0 10px;font-size:15px;line-height:1.5;color:#4f473d">
            <span style="display:inline-block;width:8px;height:8px;margin-right:10px;border-radius:999px;background:#1c1915;vertical-align:middle"></span>
            {html.escape(point)}
          </td>
        </tr>
        """
        for point in points
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f4f1ea;font:16px/1.55 'Segoe UI',system-ui,-apple-system,sans-serif;color:#1c1915">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0">{html.escape(lead)}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1ea;border-collapse:collapse">
    <tr>
      <td align="center" style="padding:36px 16px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;border-collapse:collapse">
          <tr>
            <td style="padding:0 4px 18px;font-weight:700;letter-spacing:-0.03em;font-size:20px;color:#1c1915">
              {html.escape(eyebrow)}
            </td>
          </tr>
          <tr>
            <td style="background:#ffffff;border:1px solid rgba(28,25,21,0.08);border-radius:16px;overflow:hidden;box-shadow:0 14px 30px rgba(28,25,21,0.08)">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
                <tr>
                  <td style="padding:24px 24px 8px">
                    <h1 style="margin:0;font-size:24px;line-height:1.25;letter-spacing:-0.03em;font-weight:700;color:#1c1915">
                      {html.escape(title)}
                    </h1>
                    <p style="margin:12px 0 0;font-size:15px;line-height:1.55;color:#4f473d">
                      {html.escape(lead)}
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:16px 24px 4px">
                    <div style="background:#faf7f2;border:1px solid rgba(28,25,21,0.08);border-radius:14px;padding:16px 18px">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
                        {items}
                      </table>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:22px 24px 10px;text-align:center">
                    <a href="{html.escape(link)}"
                       style="display:inline-block;padding:14px 28px;border-radius:999px;background:#1c1915;color:#f4f1ea;font-weight:600;font-size:15px;text-decoration:none;box-shadow:0 14px 30px rgba(28,25,21,0.16)">
                      {html.escape(cta)}
                    </a>
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 24px 22px;text-align:center">
                    <p style="margin:0;font-size:13px;line-height:1.5;color:#6b645b">
                      Ссылка действует {ttl} дн. и открывает кабинет без ввода ключа.<br>
                      Если кнопка не работает: <span style="word-break:break-all;color:#4f473d">{html.escape(link)}</span>
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 8px 0;text-align:center;font-size:13px;line-height:1.5;color:#6b645b">
              {html.escape(support)}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _support_line() -> str:
    parts = []
    email = (get_setting("offer_email") or get_setting("seller_email")).strip()
    if email:
        parts.append(email)
    handle = support_username()
    if handle:
        parts.append(f"Telegram @{handle}")
    return "Поддержка: " + ", ".join(parts) if parts else "Письмо отправлено автоматически."


def send_mail(to: str, subject: str, text: str, body_html: str) -> None:
    """Сырой SMTP. Для пользовательских писем используйте _dispatch — иначе не будет записи в журнале."""
    if not enabled():
        raise RuntimeError("SMTP не настроен")
    sender = settings.smtp_from.strip() or settings.smtp_user.strip()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name.strip() or "Aimarket", sender))
    message["To"] = to
    message.set_content(text)
    message.add_alternative(body_html, subtype="html")

    mode = settings.smtp_security.strip().lower()
    host, port = settings.smtp_host.strip(), int(settings.smtp_port)
    if mode == "ssl":
        client = smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(host, port, timeout=20)
    with client:
        client.ehlo()
        if mode == "starttls":
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if settings.smtp_user.strip():
            client.login(settings.smtp_user.strip(), settings.smtp_password)
        client.send_message(message)


def _serialize_outbound(row: dict) -> dict:
    ctx = row.get("context") or {}
    if isinstance(ctx, str):
        try:
            ctx = json.loads(ctx)
        except json.JSONDecodeError:
            ctx = {}
    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]) if row["user_id"] is not None else None,
        "email": row.get("user_email") or row["to_email"],
        "to_email": row["to_email"],
        "username": row.get("username") or "",
        "first_name": row.get("first_name") or "",
        "kind": row["kind"],
        "kind_label": KIND_LABELS.get(row["kind"], row["kind"]),
        "subject": row["subject"],
        "status": row["status"],
        "attempts": int(row["attempts"] or 0),
        "last_error": row["last_error"] or "",
        "created_at": row["created_at"].isoformat() if row["created_at"] is not None else "",
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] is not None else "",
        "sent_at": row["sent_at"].isoformat() if row["sent_at"] is not None else "",
        "can_retry": row["status"] in ("failed", "pending") and row["user_id"] is not None,
    }


def list_outbound_emails(*, status: str | None = None, limit: int = 200) -> dict:
    limit = max(1, min(int(limit), 500))
    status_filter = (status or "").strip().lower()
    if status_filter and status_filter not in ("pending", "sent", "failed"):
        status_filter = ""
    with pool.connection() as conn:
        failed_count = int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM outbound_emails WHERE status = 'failed'"
            ).fetchone()["n"]
        )
        if status_filter:
            rows = conn.execute(
                """
                SELECT o.id, o.user_id, o.kind, o.to_email, o.subject, o.status, o.attempts,
                       o.last_error, o.context, o.created_at, o.updated_at, o.sent_at,
                       u.email AS user_email, u.username, u.first_name
                FROM outbound_emails o
                LEFT JOIN users u ON u.id = o.user_id
                WHERE o.status = %s
                ORDER BY o.id DESC
                LIMIT %s
                """,
                (status_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT o.id, o.user_id, o.kind, o.to_email, o.subject, o.status, o.attempts,
                       o.last_error, o.context, o.created_at, o.updated_at, o.sent_at,
                       u.email AS user_email, u.username, u.first_name
                FROM outbound_emails o
                LEFT JOIN users u ON u.id = o.user_id
                ORDER BY o.id DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
    return {
        "items": [_serialize_outbound(dict(row)) for row in rows],
        "failed_count": failed_count,
    }


def _rebuild_for_retry(row: dict) -> tuple[str, str, str, str]:
    """Пересобирает письмо с новым login-токеном. Ключи/секреты не берутся из журнала."""
    user_id = row.get("user_id")
    if user_id is None:
        raise MailerError("пользователь удалён — повторить нельзя")
    user_id = int(user_id)
    kind = row["kind"]
    ctx = row.get("context") or {}
    if isinstance(ctx, str):
        try:
            ctx = json.loads(ctx)
        except json.JSONDecodeError:
            ctx = {}

    if kind in (KIND_LOGIN, KIND_LOGIN_WELCOME):
        created = bool(ctx.get("created", kind == KIND_LOGIN_WELCOME))
        return _build_login_message(user_id, created=created)

    if kind == KIND_PAYMENT_DELAYED:
        return _build_payment_delayed_message(
            user_id,
            amount_usd=Decimal(str(ctx.get("amount_usd") or "0")),
            bonus_usd=Decimal(str(ctx.get("bonus_usd") or "0")),
        )

    if kind == KIND_PAYMENT:
        return _build_payment_message_for_user(
            user_id,
            amount_usd=Decimal(str(ctx.get("amount_usd") or "0")),
            bonus_usd=Decimal(str(ctx.get("bonus_usd") or "0")),
            balance_usd=Decimal(str(ctx.get("balance_usd") or "0")),
            first_key=bool(ctx.get("first_key")),
        )

    if kind == KIND_SUPPORT_REPLY:
        preview = str(ctx.get("preview") or "").strip()
        if not preview:
            raise MailerError("нет текста ответа для повторной отправки")
        return _build_support_reply_message(user_id, preview=preview)

    if kind == KIND_NUDGE_TOPUP:
        return _build_nudge_topup_message(user_id)

    raise MailerError(f"неизвестный тип письма: {kind}")


def retry_outbound_email(email_id: int) -> dict:
    """Ручной повтор: пересобрать письмо и отправить синхронно, увеличить attempts."""
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, kind, to_email, subject, status, attempts, last_error, context
            FROM outbound_emails
            WHERE id = %s
            """,
            (email_id,),
        ).fetchone()
    if row is None:
        raise MailerError("письмо не найдено")
    row = dict(row)
    if row["status"] == "sent":
        raise MailerError("письмо уже отправлено")
    if row["status"] not in ("failed", "pending"):
        raise MailerError("повтор недоступен")

    to_email, subject, text, body_html = _rebuild_for_retry(row)
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE outbound_emails
            SET to_email = %s, subject = %s, status = 'pending', updated_at = NOW()
            WHERE id = %s
            """,
            (to_email, subject, email_id),
        )
    ok = _attempt_send(email_id, to_email, subject, text, body_html)
    with pool.connection() as conn:
        updated = conn.execute(
            """
            SELECT o.id, o.user_id, o.kind, o.to_email, o.subject, o.status, o.attempts,
                   o.last_error, o.context, o.created_at, o.updated_at, o.sent_at,
                   u.email AS user_email, u.username, u.first_name
            FROM outbound_emails o
            LEFT JOIN users u ON u.id = o.user_id
            WHERE o.id = %s
            """,
            (email_id,),
        ).fetchone()
    item = _serialize_outbound(dict(updated))
    if not ok:
        raise MailerError(item["last_error"] or "не удалось отправить")
    return item
