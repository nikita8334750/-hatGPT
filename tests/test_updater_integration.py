from decimal import Decimal

import fakeredis.aioredis
import pytest

from app.services.provider_manager import ProviderManager
from app.services.updater import update_once
from app.storage.redis_store import RedisStore


class FakeProvider:
    name = "fake"

    async def get_latest(self, base: str):
        return "2024-01-01", {"EUR": Decimal("0.9")}


class FakeBot:
    async def send_message(self, chat_id, text):
        return None


@pytest.mark.asyncio
async def test_update_once_writes_snapshot():
    redis = fakeredis.aioredis.FakeRedis()
    store = RedisStore(redis)
    manager = ProviderManager(FakeProvider(), FakeProvider())
    await update_once(FakeBot(), store, manager, "USD", cooldown_seconds=1)

    snapshot = await store.get_rates_snapshot("USD")
    assert snapshot is not None
    assert snapshot.rates["EUR"] == Decimal("0.9")
