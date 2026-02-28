import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.providers.base import RatesProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderState:
    failure_count: int = 0
    fallback_until: datetime | None = None


class ProviderManager:
    def __init__(self, primary: RatesProvider, fallback: RatesProvider):
        self._primary = primary
        self._fallback = fallback
        self._state = ProviderState()

    def _in_fallback_window(self) -> bool:
        if not self._state.fallback_until:
            return False
        return datetime.now(timezone.utc) < self._state.fallback_until

    def active_provider(self) -> RatesProvider:
        if self._in_fallback_window():
            return self._fallback
        return self._primary

    def record_success(self) -> None:
        self._state.failure_count = 0
        self._state.fallback_until = None

    def record_failure(self) -> None:
        self._state.failure_count += 1
        if self._state.failure_count >= 5:
            self._state.fallback_until = datetime.now(timezone.utc) + timedelta(minutes=10)
            logger.warning("Circuit breaker tripped; switching to fallback provider")

    def provider_name(self) -> str:
        return self.active_provider().name
