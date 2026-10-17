-- Схема PostgreSQL Aimarket.
-- Идемпотентно: docker-entrypoint-initdb.d и backend ensure_schema() при каждом старте.
-- CREATE TABLE — целевая форма для новой БД.
-- ALTER ADD COLUMN IF NOT EXISTS — апгрейд уже существующих инстансов.

-- ---------------------------------------------------------------------------
-- Пользователи
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                          BIGSERIAL PRIMARY KEY,
    telegram_id                 BIGINT UNIQUE,
    username                    TEXT NOT NULL DEFAULT '',
    first_name                  TEXT NOT NULL DEFAULT '',
    email                       TEXT NOT NULL DEFAULT '',
    balance_kopecks             BIGINT NOT NULL DEFAULT 0 CHECK (balance_kopecks >= 0),
    balance_usd                 NUMERIC(12, 4) NOT NULL DEFAULT 0,
    offer_accepted_at           TIMESTAMPTZ,
    offer_reminder_sent_at      TIMESTAMPTZ,
    blocked_at                  TIMESTAMPTZ,
    blocked_reason              TEXT NOT NULL DEFAULT '',
    notify_spend                BOOLEAN NOT NULL DEFAULT FALSE,
    notify_low_balance          BOOLEAN NOT NULL DEFAULT TRUE,
    notify_limit_exhausted      BOOLEAN NOT NULL DEFAULT TRUE,
    notify_topup                BOOLEAN NOT NULL DEFAULT TRUE,
    notify_support_email        BOOLEAN NOT NULL DEFAULT TRUE,
    support_mail_sent_at        TIMESTAMPTZ,
    nudge_topup_sent_at         TIMESTAMPTZ,
    low_balance_notified_at     TIMESTAMPTZ,
    referral_token              TEXT NOT NULL DEFAULT '',
    email_login_hash            TEXT NOT NULL DEFAULT '',
    email_login_expires_at      TIMESTAMPTZ,
    support_telegram_topic_id   BIGINT,
    support_telegram_synced_id  BIGINT,
    support_seen_at             TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_usd NUMERIC(12, 4) NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS offer_accepted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS offer_reminder_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_spend BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_low_balance BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_limit_exhausted BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_topup BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_support_email BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS support_mail_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS nudge_topup_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS low_balance_notified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_token TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_login_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_login_expires_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS support_telegram_topic_id BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS support_telegram_synced_id BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS support_seen_at TIMESTAMPTZ;
ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_balance_usd_check;
ALTER TABLE users DROP COLUMN IF EXISTS nudge_usage_sent_at;

CREATE INDEX IF NOT EXISTS idx_users_referral_token
    ON users (referral_token) WHERE referral_token <> '';
CREATE INDEX IF NOT EXISTS idx_users_email
    ON users (lower(email)) WHERE email <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_support_topic
    ON users (support_telegram_topic_id) WHERE support_telegram_topic_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- API-ключи
-- frozen_at: ключ на паузе (квота у поставщика = 0, balance_usd локально)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_keys (
    id                          BIGSERIAL PRIMARY KEY,
    user_id                     BIGINT NOT NULL REFERENCES users (id),
    name                        TEXT NOT NULL DEFAULT '',
    prefix                      TEXT NOT NULL,
    secret_hash                 TEXT NOT NULL UNIQUE,
    secret                      TEXT NOT NULL DEFAULT '',
    upstream_id                 BIGINT,
    quota_usd                   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    limit_exhausted_notified_at TIMESTAMPTZ,
    frozen_at                   TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at                  TIMESTAMPTZ
);

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS upstream_id BIGINT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS quota_usd NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS secret TEXT NOT NULL DEFAULT '';
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS limit_exhausted_notified_at TIMESTAMPTZ;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS frozen_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_api_keys_user
    ON api_keys (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_keys_frozen
    ON api_keys (frozen_at)
    WHERE frozen_at IS NOT NULL AND revoked_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_one_active
    ON api_keys (user_id) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- Ledger клиентов
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ledger (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users (id),
    amount_kopecks BIGINT NOT NULL,
    kind           TEXT NOT NULL,
    note           TEXT NOT NULL DEFAULT '',
    amount_usd     NUMERIC(12, 4) NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE ledger ADD COLUMN IF NOT EXISTS amount_usd NUMERIC(12, 4) NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_ledger_user
    ON ledger (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_topup_note
    ON ledger (note) WHERE kind = 'topup' AND note <> '';

-- ---------------------------------------------------------------------------
-- Usage (списания за запросы)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usage (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL REFERENCES users (id),
    api_key_id        BIGINT REFERENCES api_keys (id),
    upstream_log_id   BIGINT,
    request_id        TEXT NOT NULL DEFAULT '',
    model_name        TEXT NOT NULL DEFAULT '',
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    quota_units       BIGINT NOT NULL DEFAULT 0 CHECK (quota_units >= 0),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE usage ADD COLUMN IF NOT EXISTS request_id TEXT NOT NULL DEFAULT '';

DROP INDEX IF EXISTS idx_usage_upstream_log;
CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_user_upstream_log
    ON usage (user_id, upstream_log_id) WHERE upstream_log_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_user_request
    ON usage (user_id, request_id) WHERE request_id <> '';
CREATE INDEX IF NOT EXISTS idx_usage_user_time
    ON usage (user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Пополнения ЮKassa
-- status: pending | awaiting_supplier | paid | failed | rejected
-- payment_remaining_usd / bonus_remaining_usd — остатки по платежу (FIFO)
-- refund_window_ends_at — конец 14-дневного окна возврата
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topups (
    id                     BIGSERIAL PRIMARY KEY,
    user_id                BIGINT NOT NULL REFERENCES users (id),
    amount_kopecks         BIGINT NOT NULL CHECK (amount_kopecks > 0),
    amount_usd             NUMERIC(12, 4) NOT NULL DEFAULT 0,
    bonus_usd              NUMERIC(12, 4) NOT NULL DEFAULT 0,
    payment_remaining_usd  NUMERIC(12, 4) NOT NULL DEFAULT 0,
    bonus_remaining_usd    NUMERIC(12, 4) NOT NULL DEFAULT 0,
    refund_window_ends_at  TIMESTAMPTZ,
    buckets_initialized    BOOLEAN NOT NULL DEFAULT FALSE,
    status                 TEXT NOT NULL DEFAULT 'pending',
    payment_id             TEXT,
    return_token_hash      TEXT NOT NULL DEFAULT '',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at             TIMESTAMPTZ
);

ALTER TABLE topups ADD COLUMN IF NOT EXISTS payment_id TEXT;
ALTER TABLE topups ADD COLUMN IF NOT EXISTS return_token_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE topups ADD COLUMN IF NOT EXISTS bonus_usd NUMERIC(12, 4) NOT NULL DEFAULT 0;
ALTER TABLE topups ADD COLUMN IF NOT EXISTS payment_remaining_usd NUMERIC(12, 4) NOT NULL DEFAULT 0;
ALTER TABLE topups ADD COLUMN IF NOT EXISTS bonus_remaining_usd NUMERIC(12, 4) NOT NULL DEFAULT 0;
ALTER TABLE topups ADD COLUMN IF NOT EXISTS refund_window_ends_at TIMESTAMPTZ;
ALTER TABLE topups ADD COLUMN IF NOT EXISTS buckets_initialized BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_topups_status
    ON topups (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_topups_refund_window
    ON topups (status, refund_window_ends_at)
    WHERE status = 'paid' AND payment_remaining_usd > 0;
CREATE UNIQUE INDEX IF NOT EXISTS idx_topups_payment
    ON topups (payment_id) WHERE payment_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Рефералы
-- owner_user_id — персональная ссылка пользователя (после первой оплаты)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referral_groups (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referral_links (
    id             BIGSERIAL PRIMARY KEY,
    token          TEXT NOT NULL UNIQUE,
    group_id       BIGINT REFERENCES referral_groups (id) ON DELETE SET NULL,
    owner_user_id  BIGINT REFERENCES users (id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE referral_links ADD COLUMN IF NOT EXISTS group_id BIGINT
    REFERENCES referral_groups (id) ON DELETE SET NULL;
ALTER TABLE referral_links ADD COLUMN IF NOT EXISTS owner_user_id BIGINT
    REFERENCES users (id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_referral_links_group
    ON referral_links (group_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_referral_links_owner
    ON referral_links (owner_user_id) WHERE owner_user_id IS NOT NULL;

INSERT INTO referral_links (token) VALUES ('web')
ON CONFLICT (token) DO NOTHING;

CREATE TABLE IF NOT EXISTS referral_clicks (
    id          BIGSERIAL PRIMARY KEY,
    token       TEXT NOT NULL,
    visitor_key TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_referral_clicks_token
    ON referral_clicks (token, created_at DESC);

-- Один клик на visitor_key на токен (без накрутки F5).
DROP INDEX IF EXISTS idx_referral_clicks_visitor;
DELETE FROM referral_clicks a
    USING referral_clicks b
WHERE a.id > b.id
  AND a.token = b.token
  AND a.visitor_key = b.visitor_key
  AND a.visitor_key <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_referral_clicks_visitor
    ON referral_clicks (token, visitor_key)
    WHERE visitor_key <> '';

-- ---------------------------------------------------------------------------
-- Install tokens
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS install_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users (id),
    app        TEXT NOT NULL,
    os         TEXT NOT NULL,
    action     TEXT NOT NULL DEFAULT 'setup',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_install_tokens_expires
    ON install_tokens (expires_at);

-- ---------------------------------------------------------------------------
-- Поддержка
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS support_guests (
    id                 BIGSERIAL PRIMARY KEY,
    token_hash         TEXT NOT NULL UNIQUE,
    telegram_topic_id  BIGINT,
    telegram_synced_id BIGINT,
    seen_at            TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE support_guests ADD COLUMN IF NOT EXISTS telegram_topic_id BIGINT;
ALTER TABLE support_guests ADD COLUMN IF NOT EXISTS telegram_synced_id BIGINT;
ALTER TABLE support_guests ADD COLUMN IF NOT EXISTS seen_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_support_guests_topic
    ON support_guests (telegram_topic_id) WHERE telegram_topic_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS support_messages (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users (id) ON DELETE CASCADE,
    guest_id    BIGINT REFERENCES support_guests (id) ON DELETE CASCADE,
    author_kind TEXT NOT NULL CHECK (author_kind IN ('user', 'staff')),
    source      TEXT NOT NULL DEFAULT 'site' CHECK (source IN ('site', 'telegram')),
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (user_id IS NOT NULL AND guest_id IS NULL)
        OR (user_id IS NULL AND guest_id IS NOT NULL)
    )
);

ALTER TABLE support_messages ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE support_messages ADD COLUMN IF NOT EXISTS guest_id BIGINT
    REFERENCES support_guests (id) ON DELETE CASCADE;
ALTER TABLE support_messages ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'site';
ALTER TABLE support_messages DROP CONSTRAINT IF EXISTS support_messages_source_check;
ALTER TABLE support_messages ADD CONSTRAINT support_messages_source_check
    CHECK (source IN ('site', 'telegram'));

CREATE INDEX IF NOT EXISTS idx_support_messages_user
    ON support_messages (user_id, created_at) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_support_messages_guest
    ON support_messages (guest_id, created_at) WHERE guest_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Настройки
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

INSERT INTO app_settings (key, value) VALUES
    ('supplier_usd_price_rub', ''),
    ('referral_bonus_percent', '20')
ON CONFLICT (key) DO NOTHING;

UPDATE app_settings
SET value = '20'
WHERE key = 'referral_bonus_percent' AND BTRIM(value) = '';

-- ---------------------------------------------------------------------------
-- Бухгалтерия компании
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS finance_categories (
    id          BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    color        TEXT NOT NULL DEFAULT '#6b645b',
    kind         TEXT NOT NULL DEFAULT 'expense'
                     CHECK (kind IN ('expense', 'withdrawal')),
    sort_order   INTEGER NOT NULL DEFAULT 0,
    archived_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_finance_categories_kind
    ON finance_categories (kind, sort_order, id);

CREATE TABLE IF NOT EXISTS finance_accounts (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    provider_key TEXT NOT NULL DEFAULT '',
    is_default   BOOLEAN NOT NULL DEFAULT FALSE,
    note         TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_finance_accounts_provider
    ON finance_accounts (provider_key) WHERE provider_key <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_finance_accounts_default
    ON finance_accounts (is_default) WHERE is_default;

CREATE TABLE IF NOT EXISTS finance_operations (
    id                       BIGSERIAL PRIMARY KEY,
    kind                     TEXT NOT NULL CHECK (kind IN (
        'income', 'expense', 'withdrawal', 'deposit', 'transfer'
    )),
    account_id               BIGINT NOT NULL REFERENCES finance_accounts (id),
    counterparty_account_id  BIGINT REFERENCES finance_accounts (id),
    category_id              BIGINT REFERENCES finance_categories (id) ON DELETE SET NULL,
    amount_rub               NUMERIC(14, 2) NOT NULL CHECK (amount_rub > 0),
    amount_usd               NUMERIC(12, 4) NOT NULL DEFAULT 0 CHECK (amount_usd >= 0),
    note                     TEXT NOT NULL DEFAULT '',
    occurred_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source                   TEXT NOT NULL DEFAULT 'manual',
    source_ref               TEXT NOT NULL DEFAULT '',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (kind <> 'transfer' AND counterparty_account_id IS NULL)
        OR (kind = 'transfer' AND counterparty_account_id IS NOT NULL
            AND counterparty_account_id <> account_id)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_finance_operations_source
    ON finance_operations (source, source_ref) WHERE source_ref <> '';
CREATE INDEX IF NOT EXISTS idx_finance_operations_kind_time
    ON finance_operations (kind, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_finance_operations_account
    ON finance_operations (account_id, occurred_at DESC);

INSERT INTO finance_categories (name, color, kind, sort_order)
SELECT v.name, v.color, v.kind, v.sort_order
FROM (VALUES
    ('Комиссия', '#8d2b2b', 'expense', 10),
    ('Реклама', '#9a6700', 'expense', 20),
    ('Хостинг', '#2f4f8c', 'expense', 30),
    ('Налоги', '#6b645b', 'expense', 40),
    ('Пополнение поставщика', '#2a6f97', 'expense', 50),
    ('Прочее', '#5c564c', 'expense', 90),
    ('Вывод владельцу', '#1c1915', 'withdrawal', 10),
    ('Прочее', '#6b645b', 'withdrawal', 90)
) AS v(name, color, kind, sort_order)
WHERE NOT EXISTS (SELECT 1 FROM finance_categories LIMIT 1);

-- ---------------------------------------------------------------------------
-- Журнал исходящих SMTP-писем (без тела — только метаданные для админки)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outbound_emails (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users (id) ON DELETE SET NULL,
    kind        TEXT NOT NULL,
    to_email    TEXT NOT NULL,
    subject     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sent', 'failed')),
    attempts    INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error  TEXT NOT NULL DEFAULT '',
    context     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_outbound_emails_created
    ON outbound_emails (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outbound_emails_status
    ON outbound_emails (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outbound_emails_user
    ON outbound_emails (user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Уборка устаревших объектов
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS finance_entries;
DELETE FROM app_settings WHERE key = 'finance_opening_cash_rub';
