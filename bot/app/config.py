from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    telegram_bot_token: str = ""
    backend_url: str = "http://127.0.0.1:8000"
    bot_internal_token: str = ""


settings = Settings()
