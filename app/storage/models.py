from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RatesSnapshot:
    base: str
    rates: dict[str, Decimal]
    provider: str
    as_of: str
    fetched_at: str


@dataclass(frozen=True)
class HealthStatus:
    active_provider: str
    last_success_at: str | None
    last_error: str | None
    staleness_seconds: int
