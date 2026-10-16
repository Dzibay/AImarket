import logging

from app.db import pool
from app.mailer import enabled as mail_enabled
from app.mailer import send_nudge_topup_email
from app.settings_store import consent_url, offer_url, privacy_url
from app.telegram_link import notify_offer_reminder

log = logging.getLogger("app.reminders")

_BATCH = 50
# Письмо только тем, кто «только что» пересёк порог 1 суток.
# Иначе после деплоя улетит всем старым аккаунтам без оплаты.
_NUDGE_AFTER = "1 day"
_NUDGE_WITHIN = "3 days"


def send_offer_reminders() -> None:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, telegram_id
            FROM users
            WHERE offer_accepted_at IS NULL
              AND telegram_id IS NOT NULL
              AND blocked_at IS NULL
              AND offer_reminder_sent_at IS NULL
              AND created_at <= NOW() - INTERVAL '20 minutes'
            ORDER BY created_at
            LIMIT 100
            """
        ).fetchall()
    for row in rows:
        user_id = int(row["id"])
        telegram_id = int(row["telegram_id"])
        if not notify_offer_reminder(
            telegram_id,
            privacy_url=privacy_url(),
            consent_url=consent_url(),
            offer_url=offer_url(),
        ):
            continue
        with pool.connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET offer_reminder_sent_at = NOW()
                WHERE id = %s AND offer_reminder_sent_at IS NULL
                """,
                (user_id,),
            )


def send_lifecycle_emails() -> None:
    """Письмо «не пополнил» — раз в сутки после регистрации, один раз."""
    if not mail_enabled():
        return
    _send_topup_nudges()


def _send_topup_nudges() -> None:
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT u.id
            FROM users u
            WHERE u.blocked_at IS NULL
              AND u.nudge_topup_sent_at IS NULL
              AND BTRIM(u.email) <> ''
              AND u.created_at <= NOW() - INTERVAL '{_NUDGE_AFTER}'
              AND u.created_at > NOW() - INTERVAL '{_NUDGE_WITHIN}'
              AND NOT EXISTS (
                    SELECT 1 FROM topups t
                    WHERE t.user_id = u.id AND t.status = 'paid'
                  )
            ORDER BY u.created_at ASC
            LIMIT %s
            """,
            (_BATCH,),
        ).fetchall()
    for row in rows:
        user_id = int(row["id"])
        with pool.connection() as conn:
            claimed = conn.execute(
                f"""
                UPDATE users
                SET nudge_topup_sent_at = NOW()
                WHERE id = %s
                  AND nudge_topup_sent_at IS NULL
                  AND blocked_at IS NULL
                  AND BTRIM(email) <> ''
                  AND created_at <= NOW() - INTERVAL '{_NUDGE_AFTER}'
                  AND created_at > NOW() - INTERVAL '{_NUDGE_WITHIN}'
                  AND NOT EXISTS (
                        SELECT 1 FROM topups t
                        WHERE t.user_id = users.id AND t.status = 'paid'
                      )
                RETURNING email
                """,
                (user_id,),
            ).fetchone()
        if claimed is None:
            continue
        email = str(claimed["email"]).strip()
        if not email:
            continue
        try:
            send_nudge_topup_email(user_id, email)
        except Exception:
            log.exception("не удалось отправить nudge_topup user=%s", user_id)
