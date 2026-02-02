import pytest

pytest.importorskip("redis")
fakeredis = pytest.importorskip("fakeredis.aioredis")

from app.storage.redis_store import RedisStore


@pytest.mark.asyncio
async def test_get_currencies_defaults_empty():
    redis = fakeredis.FakeRedis()
    store = RedisStore(redis)
    assert await store.get_currencies("USD") == []
