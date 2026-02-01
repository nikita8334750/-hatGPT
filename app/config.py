import os
from dataclasses import dataclass


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


@dataclass(frozen=True)
class Settings:
    bot_token: str
    redis_url: str
    provider_url: str
    rates_api_key: str | None
    update_interval_seconds: int
    default_base: str
    max_staleness_seconds: int
    watch_cooldown_seconds: int
    enable_history: bool
    postgres_dsn: str | None


    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            bot_token=_get_env("BOT_TOKEN", ""),
            redis_url=_get_env("REDIS_URL", "redis://redis:6379/0"),
            provider_url=_get_env("PROVIDER_URL", "https://api.example.com/latest"),
            rates_api_key=os.getenv("RATES_API_KEY"),
            update_interval_seconds=int(_get_env("UPDATE_INTERVAL_SECONDS", "60")),
            default_base=_get_env("DEFAULT_BASE", "USD"),
            max_staleness_seconds=int(_get_env("MAX_STALENESS_SECONDS", "3600")),
            watch_cooldown_seconds=int(_get_env("WATCH_COOLDOWN_SECONDS", "300")),
            enable_history=_get_env("ENABLE_HISTORY", "false").lower() == "true",
            postgres_dsn=os.getenv("POSTGRES_DSN"),
        )
