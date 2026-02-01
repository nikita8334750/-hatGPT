from abc import ABC, abstractmethod
from decimal import Decimal


class RatesProvider(ABC):
    name: str

    @abstractmethod
    async def get_latest(self, base: str) -> tuple[str, dict[str, Decimal]]:
        raise NotImplementedError
