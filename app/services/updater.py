import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from aiogram import Bot

from app.services.provider_manager import ProviderManager
from app.services.watches import evaluate_watches
from app.storage.models import RatesSnapshot
from app.storage.redis_store import RedisStore

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _staleness_seconds(fetched_at: str) -> int:
    fetched_dt = datetime.fromisoformat(fetched_at)
    return int((datetime.now(timezone.utc) - fetched_dt).total_seconds())


async def run_updater(
    bot: Bot,
    store: RedisStore,
    manager: ProviderManager,
    base: str,
    interval_seconds: int,
    cooldown_seconds: int,
    history_writer: Callable[[RatesSnapshot], Awaitable[None]] | None = None,
) -> None:
    while True:
        bases = await store.list_bases()
        if not bases:
            bases = [base]
        for base_currency in bases:
            await update_once(
                bot,
                store,
                manager,
                base_currency,
                cooldown_seconds,
                history_writer,
            )
        await asyncio.sleep(interval_seconds)


async def update_once(
    bot: Bot,
    store: RedisStore,
    manager: ProviderManager,
    base: str,
    cooldown_seconds: int,
    history_writer: Callable[[RatesSnapshot], Awaitable[None]] | None = None,
) -> None:
    provider = manager.active_provider()
    try:
        as_of, rates = await provider.get_latest(base)
        snapshot = RatesSnapshot(
            base=base,
            rates=rates,
            provider=provider.name,
            as_of=as_of,
            fetched_at=_now_iso(),
        )
        await store.set_rates_snapshot(snapshot)
        staleness = _staleness_seconds(snapshot.fetched_at)
        await store.set_last_success(provider.name, staleness)
        if history_writer:
            await history_writer(snapshot)
        await evaluate_watches(bot, store, snapshot, cooldown_seconds)
        manager.record_success()
        logger.info("Rates updated using %s", provider.name)
    except Exception as exc:
        manager.record_failure()
        await store.set_last_error(str(exc))
        logger.warning("Rates update failed: %s", exc)
