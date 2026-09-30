import logging

from app.db import pool
from app.settings_store import consent_url, offer_url, privacy_url
from app.telegram_link import notify_offer_reminder

log = logging.getLogger("app.reminders")


def send_offer_reminders() -> None:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, telegram_id
            FROM users
            WHERE offer_accepted_at IS NULL
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
