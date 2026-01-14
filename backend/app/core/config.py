from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AXIS"
    environment: str = "dev"
    debug: bool = False
    secret_key: str = "CHANGE_ME"
    access_token_expire_minutes: int = 60 * 24

    database_url: str = "postgresql+psycopg2://axis:axis@db:5432/axis"
    redis_url: str = "redis://redis:6379/0"

    cors_origins: str = "*"
    rate_limit_per_minute: int = 60

    ai_provider: str = "mock"
    ai_api_key: str | None = None

    mercadolivre_rate_limit_per_minute: int = 10
    mercadolivre_headless: bool = True
    mercadolivre_min_delay_seconds: int = 1
    mercadolivre_max_delay_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
