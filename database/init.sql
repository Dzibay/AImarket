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

CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_upstream_log
    ON usage (upstream_log_id) WHERE upstream_log_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_usage_user_time ON usage (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_topup_note
    ON ledger (note) WHERE kind = 'topup' AND note <> '';

-- Заявки на пополнение. Деньги зачисляет админ после оплаты.
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

CREATE INDEX IF NOT EXISTS idx_topups_status ON topups (status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_topups_payment
    ON topups (payment_id) WHERE payment_id IS NOT NULL;

-- Настройки админки: корневой ключ, цена, реквизиты, текст оферты.
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
