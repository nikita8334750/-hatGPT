from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "smart-telegram-assistant"
    environment: str = "local"
    log_level: str = "INFO"

    bot_token: str = Field(..., alias="BOT_TOKEN")
    webhook_secret: str = Field(..., alias="WEBHOOK_SECRET")
    webhook_url: str = Field(..., alias="WEBHOOK_URL")

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")

    default_timezone: str = Field("Europe/Berlin", alias="DEFAULT_TIMEZONE")
    dnd_start: str = Field("22:00", alias="DND_START")
    dnd_end: str = Field("08:00", alias="DND_END")

    metrics_enabled: bool = Field(True, alias="METRICS_ENABLED")


@lru_cache

def get_settings() -> Settings:
    return Settings()
