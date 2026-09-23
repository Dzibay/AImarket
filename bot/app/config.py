from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _dotenv() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.yml").is_file():
            env = parent / ".env"
            return env if env.is_file() else None
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_dotenv(), extra="ignore")

    telegram_bot_token: str = ""
    backend_url: str = "http://127.0.0.1:8000"
    bot_internal_token: str = ""


settings = Settings()
