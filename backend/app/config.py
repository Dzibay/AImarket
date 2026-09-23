from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    app_name: str = "Aimarket"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "aimarket"
    db_user: str = "aimarket"
    db_password: str = "aimarket"

    # Секрет, которым бот доказывает, что ходит во внутреннее API.
    bot_internal_token: str = ""
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    max_keys_per_user: int = 5

    # Корневой ключ кабинета router.cheap. Покупателям его не отдаём.
    router_base_url: str = "https://router.cheap"
    router_root_key: str = ""
    # Сколько внутренних единиц квоты в $1. Берётся из /api/status.
    router_quota_per_unit: int = 500000
    # Розница: копеек за $1 лимита на ключе. 0 — продажа закрыта, пока админ не задаст цену.
    usd_price_kopecks: int = 0
    public_base_url: str = ""
    sync_interval_sec: int = 60

    admin_password: str = ""
    admin_token_secret: str = ""
    admin_token_ttl_hours: int = 12

    # ЮKassa: shopId и секретный ключ из кабинета магазина.
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    # Почта для чека, если в кабинете включены чеки. Код НДС: 1 — без НДС.
    yookassa_receipt_email: str = ""
    yookassa_vat_code: int = 1

    @property
    def dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )


settings = Settings()
