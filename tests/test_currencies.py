from decimal import Decimal

import pytest

pytest.importorskip("redis")
fakeredis = pytest.importorskip("fakeredis.aioredis")

from app.storage.models import RatesSnapshot
from app.storage.redis_store import RedisStore


@pytest.mark.asyncio
async def test_get_currencies_defaults_empty():
    redis = fakeredis.FakeRedis()
    store = RedisStore(redis)
    assert await store.get_currencies("USD") == []


@pytest.mark.asyncio
async def test_get_currencies_from_snapshot():
    redis = fakeredis.FakeRedis()
    store = RedisStore(redis)
    snapshot = RatesSnapshot(
        base="USD",
        rates={"EUR": Decimal("0.9"), "JPY": Decimal("110")},
        provider="test",
        as_of="2024-01-01",
        fetched_at="2024-01-01T00:00:00+00:00",
    )
    await store.set_rates_snapshot(snapshot)
    currencies = await store.get_currencies("USD")
    assert currencies == ["EUR", "JPY", "USD"]
