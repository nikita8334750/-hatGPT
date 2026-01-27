from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from redis import Redis


@dataclass
class DialogState:
    state: str
    payload: dict[str, Any]


class DialogManager:
    def __init__(self, redis: Redis, ttl_seconds: int = 900) -> None:
        self.redis = redis
        self.ttl = ttl_seconds

    def get_state(self, user_id: int) -> DialogState | None:
        raw = self.redis.get(self._key(user_id))
        if not raw:
            return None
        data = json.loads(raw)
        return DialogState(state=data["state"], payload=data.get("payload", {}))

    def set_state(self, user_id: int, state: str, payload: dict[str, Any]) -> None:
        value = json.dumps({"state": state, "payload": payload})
        self.redis.set(self._key(user_id), value, ex=self.ttl)

    def clear_state(self, user_id: int) -> None:
        self.redis.delete(self._key(user_id))

    def _key(self, user_id: int) -> str:
        return f"dialog:{user_id}"
