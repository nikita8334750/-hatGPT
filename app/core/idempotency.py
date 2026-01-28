from __future__ import annotations

from datetime import timedelta

from redis import Redis


class IdempotencyStore:
    def __init__(self, redis: Redis, ttl_seconds: int = 3600) -> None:
        self.redis = redis
        self.ttl = ttl_seconds

    def seen(self, key: str) -> bool:
        return self.redis.exists(key) == 1

    def mark(self, key: str) -> None:
        self.redis.set(key, "1", ex=self.ttl)


class RateLimiter:
    def __init__(self, redis: Redis, limit: int = 20, window_seconds: int = 60) -> None:
        self.redis = redis
        self.limit = limit
        self.window = window_seconds

    def allow(self, key: str) -> bool:
        current = self.redis.incr(key)
        if current == 1:
            self.redis.expire(key, self.window)
        return current <= self.limit
