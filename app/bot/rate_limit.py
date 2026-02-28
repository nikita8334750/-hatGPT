import time
from dataclasses import dataclass


@dataclass
class RateLimiter:
    ttl_seconds: int
    _last_seen: dict[int, float]

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._last_seen = {}

    def allow(self, chat_id: int) -> bool:
        now = time.monotonic()
        last_seen = self._last_seen.get(chat_id)
        if last_seen is not None and now - last_seen < self.ttl_seconds:
            return False
        self._last_seen[chat_id] = now
        return True
