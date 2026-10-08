-- Схема PostgreSQL для Aimarket.
-- Идемпотентно: первый старт контейнера postgres (docker-entrypoint-initdb.d)
-- и повторно backend при старте (ensure_schema).

CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT NOT NULL UNIQUE,
    username        TEXT NOT NULL DEFAULT '',
    first_name      TEXT NOT NULL DEFAULT '',
    balance_kopecks BIGINT NOT NULL DEFAULT 0 CHECK (balance_kopecks >= 0),
    balance_usd     NUMERIC(12, 4) NOT NULL DEFAULT 0 CHECK (balance_usd >= 0),
    offer_accepted_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_usd NUMERIC(12, 4) NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS offer_accepted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS offer_reminder_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_spend BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_low_balance BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_limit_exhausted BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_topup BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS low_balance_notified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_token TEXT NOT NULL DEFAULT '';
-- Пользователи с сайта: без Telegram, вход по API-ключу, почта для писем.
ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_users_referral_token
    ON users (referral_token) WHERE referral_token <> '';
CREATE INDEX IF NOT EXISTS idx_users_email
    ON users (lower(email)) WHERE email <> '';

CREATE TABLE IF NOT EXISTS products (
    id                     BIGSERIAL PRIMARY KEY,
    slug                   TEXT NOT NULL UNIQUE,
    title                  TEXT NOT NULL,
    description            TEXT NOT NULL DEFAULT '',
    price_per_1k_kopecks   INTEGER NOT NULL CHECK (price_per_1k_kopecks > 0),
    active                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ключ покупателя. Секрет нужен боту, чтобы пользователь мог скопировать его снова.
CREATE TABLE IF NOT EXISTS api_keys (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users (id),
    name        TEXT NOT NULL DEFAULT '',
    prefix      TEXT NOT NULL,
    secret_hash TEXT NOT NULL UNIQUE,
    secret      TEXT NOT NULL DEFAULT '',
    upstream_id BIGINT,
    quota_usd   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ
);

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS upstream_id BIGINT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS quota_usd NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS secret TEXT NOT NULL DEFAULT '';
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS limit_exhausted_notified_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_one_active
    ON api_keys (user_id) WHERE revoked_at IS NULL;

-- Движения баланса: пополнение и списание за токены.
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

CREATE INDEX IF NOT EXISTS idx_ledger_user ON ledger (user_id, created_at DESC);

-- Детальный расход: один запрос к модели — одна строка. quota_units — внутренние единицы router.cheap.
CREATE TABLE IF NOT EXISTS usage (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL REFERENCES users (id),
    api_key_id        BIGINT REFERENCES api_keys (id),
    upstream_log_id   BIGINT,
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
CREATE INDEX IF NOT EXISTS idx_usage_user_time ON usage (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_topup_note
    ON ledger (note) WHERE kind = 'topup' AND note <> '';

-- Платежи ЮKassa. Баланс зачисляется автоматически после успешной оплаты.
CREATE TABLE IF NOT EXISTS topups (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users (id),
    amount_kopecks BIGINT NOT NULL CHECK (amount_kopecks > 0),
    amount_usd     NUMERIC(12, 4) NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'pending',
    payment_id     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at     TIMESTAMPTZ
);

ALTER TABLE topups ADD COLUMN IF NOT EXISTS payment_id TEXT;
-- Платежи с сайта: хэш одноразового токена из return_url, по нему логиним в кабинет.
ALTER TABLE topups ADD COLUMN IF NOT EXISTS return_token_hash TEXT NOT NULL DEFAULT '';
-- Бонус к пополнению (из админки), зачисляется сверх amount_usd.
ALTER TABLE topups ADD COLUMN IF NOT EXISTS bonus_usd NUMERIC(12, 4) NOT NULL DEFAULT 0;
-- Вход по ссылке из письма: хэш токена и срок действия.
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_login_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_login_expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_topups_status ON topups (status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_topups_payment
    ON topups (payment_id) WHERE payment_id IS NOT NULL;

-- Реферальные ссылки: токен в deep link бота (?start=token).
CREATE TABLE IF NOT EXISTS referral_groups (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referral_links (
    id         BIGSERIAL PRIMARY KEY,
    token      TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE referral_links ADD COLUMN IF NOT EXISTS group_id BIGINT REFERENCES referral_groups (id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_referral_links_group ON referral_links (group_id);

-- Системный токен для переходов с сайта в бота (кнопка «Открыть бота»).
INSERT INTO referral_links (token) VALUES ('web') ON CONFLICT (token) DO NOTHING;

-- Установка одной командой: хэш токена из ссылки /i/{token}, программа, система и действие.
CREATE TABLE IF NOT EXISTS install_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users (id),
    app        TEXT NOT NULL,
    os         TEXT NOT NULL,
    action     TEXT NOT NULL DEFAULT 'setup',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_install_tokens_expires ON install_tokens (expires_at);

-- Гостевые сессии чата поддержки (токен в localStorage браузера).
CREATE TABLE IF NOT EXISTS support_guests (
    id         BIGSERIAL PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    seen_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Тема форума в Telegram-группе поддержки (message_thread_id).
ALTER TABLE support_guests ADD COLUMN IF NOT EXISTS telegram_topic_id BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS support_telegram_topic_id BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_support_guests_topic
    ON support_guests (telegram_topic_id) WHERE telegram_topic_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_support_topic
    ON users (support_telegram_topic_id) WHERE support_telegram_topic_id IS NOT NULL;

-- Чат поддержки на сайте: сообщения пользователя/гостя и ответы админки.
CREATE TABLE IF NOT EXISTS support_messages (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users (id) ON DELETE CASCADE,
    guest_id    BIGINT REFERENCES support_guests (id) ON DELETE CASCADE,
    author_kind TEXT NOT NULL CHECK (author_kind IN ('user', 'staff')),
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (user_id IS NOT NULL AND guest_id IS NULL)
        OR (user_id IS NULL AND guest_id IS NOT NULL)
    )
);

-- Старые инсталляции: user_id был NOT NULL, guest_id не было.
ALTER TABLE support_messages ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE support_messages ADD COLUMN IF NOT EXISTS guest_id BIGINT REFERENCES support_guests (id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_support_messages_user
    ON support_messages (user_id, created_at) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_support_messages_guest
    ON support_messages (guest_id, created_at) WHERE guest_id IS NOT NULL;

-- Когда пользователь последний раз открывал чат (для бейджа непрочитанных ответов).
ALTER TABLE users ADD COLUMN IF NOT EXISTS support_seen_at TIMESTAMPTZ;

-- Настройки админки: корневой ключ, цена, продавец, текст оферты.
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

INSERT INTO products (slug, title, description, price_per_1k_kopecks)
VALUES
    ('gpt-4o', 'GPT-4o', 'Токены для запросов к GPT-4o. Цена за 1000 токенов.', 150),
    ('claude', 'Claude', 'Токены для запросов к Claude. Цена за 1000 токенов.', 180),
    ('gemini', 'Gemini', 'Токены для запросов к Gemini. Цена за 1000 токенов.', 80)
ON CONFLICT (slug) DO NOTHING;
