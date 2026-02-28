from decimal import Decimal

import httpx

from app.providers.base import RatesProvider
from app.providers.http import request_with_retries


class FreeFallbackProvider(RatesProvider):
    name = "free-fallback"

    def __init__(self, base_url: str = "https://api.frankfurter.app/latest"):
        self._base_url = base_url

    async def get_latest(self, base: str) -> tuple[str, dict[str, Decimal]]:
        params = {"base": base}
        async with httpx.AsyncClient() as client:
            response = await request_with_retries(
                client,
                "GET",
                self._base_url,
                params=params,
            )
        payload = response.json()
        as_of = payload.get("date") or payload.get("as_of")
        rates_raw = payload.get("rates", {})
        return as_of, {k.upper(): Decimal(str(v)) for k, v in rates_raw.items()}
