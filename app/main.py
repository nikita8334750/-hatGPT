import asyncio
import logging

from aiogram import Bot, Dispatcher
from redis.asyncio import Redis

from app.bot.handlers import setup_router
from app.bot.rate_limit import RateLimiter
from app.config import Settings
from app.providers.free_fallback import FreeFallbackProvider
from app.providers.near_real_time import NearRealTimeProvider
from app.services.history import HistoryConfig, HistoryWriter
from app.services.provider_manager import ProviderManager
from app.services.updater import run_updater
from app.storage.redis_store import RedisStore

logging.basicConfig(level=logging.INFO)


def _build_history(settings: Settings) -> HistoryWriter | None:
    if not settings.enable_history or not settings.postgres_dsn:
        return None
    return HistoryWriter(HistoryConfig(dsn=settings.postgres_dsn))


async def main() -> None:
    settings = Settings.from_env()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    store = RedisStore(redis)
    await store.add_base(settings.default_base)

    primary = NearRealTimeProvider(settings.rates_api_key or "", settings.provider_url)
    fallback = FreeFallbackProvider()
    manager = ProviderManager(primary, fallback)

    history_writer = _build_history(settings)
    if history_writer:
        await history_writer.connect()

    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(
        setup_router(
            store,
            settings.default_base,
            settings.max_staleness_seconds,
            history_writer,
            RateLimiter(settings.rate_limit_seconds),
        )
    )

    updater_task = asyncio.create_task(
        run_updater(
            bot,
            store,
            manager,
            settings.default_base,
            settings.update_interval_seconds,
            settings.watch_cooldown_seconds,
            history_writer.write_snapshot if history_writer else None,
        )
    )

    try:
        await dispatcher.start_polling(bot)
    finally:
        updater_task.cancel()
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
