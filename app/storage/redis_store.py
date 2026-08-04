import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis

from app.storage.models import HealthStatus, RatesSnapshot


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RedisStore:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def set_rates_snapshot(self, snapshot: RatesSnapshot) -> None:
        payload = {
            "base": snapshot.base,
            "rates": {k: str(v) for k, v in snapshot.rates.items()},
            "provider": snapshot.provider,
            "as_of": snapshot.as_of,
            "fetched_at": snapshot.fetched_at,
        }
        await self._redis.set(f"rates:{snapshot.base}", json.dumps(payload))
        currencies = sorted({snapshot.base, *snapshot.rates.keys()})
        await self._redis.set(f"currencies:{snapshot.base}", json.dumps(currencies))

    async def get_rates_snapshot(self, base: str) -> RatesSnapshot | None:
        raw = await self._redis.get(f"rates:{base}")
        if not raw:
            return None
        data = json.loads(raw)
        return RatesSnapshot(
            base=data["base"],
            rates={k: Decimal(v) for k, v in data["rates"].items()},
            provider=data["provider"],
            as_of=data["as_of"],
            fetched_at=data["fetched_at"],
        )

    async def get_currencies(self, base: str) -> list[str]:
        raw = await self._redis.get(f"currencies:{base}")
        if not raw:
            return []
        return json.loads(raw)

    async def set_health(self, health: HealthStatus) -> None:
        payload = {
            "active_provider": health.active_provider,
            "last_success_at": health.last_success_at,
            "last_error": health.last_error,
            "staleness_seconds": health.staleness_seconds,
        }
        await self._redis.set("health", json.dumps(payload))

    async def get_health(self) -> HealthStatus | None:
        raw = await self._redis.get("health")
        if not raw:
            return None
        data = json.loads(raw)
        return HealthStatus(
            active_provider=data.get("active_provider", "unknown"),
            last_success_at=data.get("last_success_at"),
            last_error=data.get("last_error"),
            staleness_seconds=int(data.get("staleness_seconds", 0)),
        )

    async def set_chat_base(self, chat_id: int, base: str) -> None:
        if not base.isalpha() or len(base) > 3:
            raise ValueError("Invalid currency code")
        await self._redis.set(f"chat:{chat_id}:base", base.upper())
        await self._redis.sadd("bases", base.upper())

    async def get_chat_base(self, chat_id: int) -> str | None:
        raw = await self._redis.get(f"chat:{chat_id}:base")
        return raw.decode() if raw else None

    async def add_base(self, base: str) -> None:
        if not base.isalpha() or len(base) > 3:
            raise ValueError("Invalid currency code")
        await self._redis.sadd("bases", base.upper())

    async def list_bases(self) -> list[str]:
        bases = await self._redis.smembers("bases")
        return [base.decode() if isinstance(base, bytes) else base for base in bases]

    async def set_chat_precision(self, chat_id: int, precision: int) -> None:
        await self._redis.set(f"chat:{chat_id}:precision", str(precision))

    async def get_chat_precision(self, chat_id: int) -> int | None:
        raw = await self._redis.get(f"chat:{chat_id}:precision")
        return int(raw) if raw else None

    async def add_watch(self, chat_id: int, watch: dict[str, Any]) -> None:
        key = f"chat:{chat_id}:watches"
        raw = await self._redis.get(key)
        watches = json.loads(raw) if raw else []
        watches.append(watch)
        await self._redis.set(key, json.dumps(watches))
        await self._redis.sadd("watches:chats", chat_id)

    async def list_watches(self, chat_id: int) -> list[dict[str, Any]]:
        raw = await self._redis.get(f"chat:{chat_id}:watches")
        return json.loads(raw) if raw else []

    async def set_watches(self, chat_id: int, watches: list[dict[str, Any]]) -> None:
        await self._redis.set(f"chat:{chat_id}:watches", json.dumps(watches))

    async def list_watch_chats(self) -> list[int]:
        ids = await self._redis.smembers("watches:chats")
        return [int(i) for i in ids]

    async def update_watch_last_notified(self, chat_id: int, watch_id: str, timestamp: str) -> None:
        watches = await self.list_watches(chat_id)
        updated = []
        for watch in watches:
            if watch["id"] == watch_id:
                watch = {**watch, "last_notified_at": timestamp}
            updated.append(watch)
        await self.set_watches(chat_id, updated)

    async def remove_watch(self, chat_id: int, watch_id: str) -> bool:
        watches = await self.list_watches(chat_id)
        remaining = [watch for watch in watches if watch["id"] != watch_id]
        if len(remaining) == len(watches):
            return False
        await self.set_watches(chat_id, remaining)
        return True

    async def set_last_error(self, error: str) -> None:
        health = await self.get_health() or HealthStatus("unknown", None, None, 0)
        await self.set_health(
            HealthStatus(
                active_provider=health.active_provider,
                last_success_at=health.last_success_at,
                last_error=error[:500] if error else None,  # Limit error message size
                staleness_seconds=health.staleness_seconds,
            )
        )

    async def set_last_success(self, provider: str, staleness_seconds: int) -> None:
        await self.set_health(
            HealthStatus(
                active_provider=provider,
                last_success_at=_now_iso(),
                last_error=None,
                staleness_seconds=staleness_seconds,
            )
        )
