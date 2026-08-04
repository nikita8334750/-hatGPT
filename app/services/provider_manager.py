import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock

from app.providers.base import RatesProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderState:
    failure_count: int = 0
    fallback_until: datetime | None = None
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def record_failure(self, threshold: int = 5, fallback_minutes: int = 10) -> bool:
        """Record a failure and return True if circuit breaker tripped."""
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= threshold and not self.fallback_until:
                self.fallback_until = datetime.now(timezone.utc) + timedelta(minutes=fallback_minutes)
                logger.warning("Circuit breaker tripped; switching to fallback provider for %d minutes", fallback_minutes)
                return True
            return False

    def record_success(self) -> None:
        """Reset failure state on success."""
        with self._lock:
            self.failure_count = 0
            self.fallback_until = None

    def should_use_fallback(self) -> bool:
        """Check if fallback provider should be used."""
        with self._lock:
            if not self.fallback_until:
                return False
            if datetime.now(timezone.utc) >= self.fallback_until:
                self.fallback_until = None
                self.failure_count = 0
                logger.info("Circuit breaker reset; switching back to primary provider")
                return False
            return True


class ProviderManager:
    """Manages primary and fallback rate providers with circuit breaker pattern."""

    def __init__(self, primary: RatesProvider, fallback: RatesProvider):
        self._primary = primary
        self._fallback = fallback
        self._state = ProviderState()

    def active_provider(self) -> RatesProvider:
        """Return the currently active provider based on circuit breaker state."""
        if self._state.should_use_fallback():
            return self._fallback
        return self._primary

    def record_success(self) -> None:
        """Record a successful fetch."""
        self._state.record_success()

    def record_failure(self) -> None:
        """Record a failed fetch."""
        self._state.record_failure()

    def provider_name(self) -> str:
        """Return the name of the active provider."""
        return self.active_provider().name
