"""Письма пользователям сайта: ключ доступа и ссылка в кабинет после оплаты.

SMTP задаётся в .env. Отправка идёт в фоновом потоке, чтобы не задерживать вебхук ЮKassa.
Ссылка для входа — одноразовый токен на пользователе (users.email_login_hash), как return_url у ЮKassa.
"""

import html
import logging
import secrets
import smtplib
import ssl
import threading
from decimal import Decimal
from email.message import EmailMessage
from email.utils import formataddr

from app.config import settings
from app.db import pool
from app.settings_store import get_setting, public_base_url, support_username
from app.web_auth import key_hash

log = logging.getLogger("app.mailer")


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


def send_payment_email(
    user_id: int,
    *,
    amount_usd: Decimal,
    bonus_usd: Decimal,
    balance_usd: Decimal,
    first_key: bool,
) -> None:
    if not enabled():
        log.info("SMTP не настроен — письмо пользователю %s не отправлено", user_id)
        return
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
        return
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
    send_async(email, subject, text, body_html)


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


def _support_line() -> str:
    parts = []
    email = (get_setting("offer_email") or get_setting("seller_email")).strip()
    if email:
        parts.append(email)
    handle = support_username()
    if handle:
        parts.append(f"Telegram @{handle}")
    return "Поддержка: " + ", ".join(parts) if parts else "Письмо отправлено автоматически."


def send_async(to: str, subject: str, text: str, body_html: str) -> None:
    threading.Thread(
        target=_send_safe,
        args=(to, subject, text, body_html),
        name="mail-send",
        daemon=True,
    ).start()


def _send_safe(to: str, subject: str, text: str, body_html: str) -> None:
    try:
        send_mail(to, subject, text, body_html)
        log.info("письмо «%s» отправлено на %s", subject, to)
    except Exception:
        log.exception("не удалось отправить письмо на %s", to)


def send_mail(to: str, subject: str, text: str, body_html: str) -> None:
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
