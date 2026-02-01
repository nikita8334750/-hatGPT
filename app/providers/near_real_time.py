from decimal import Decimal

import httpx

from app.providers.base import RatesProvider
from app.providers.http import request_with_retries


class NearRealTimeProvider(RatesProvider):
    name = "near-real-time"

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url

    async def get_latest(self, base: str) -> tuple[str, dict[str, Decimal]]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        params = {"base": base}
        async with httpx.AsyncClient() as client:
            response = await request_with_retries(
                client,
                "GET",
                self._base_url,
                headers=headers,
                params=params,
            )
        payload = response.json()
        as_of = payload.get("as_of") or payload.get("date")
        rates_raw = payload.get("rates", {})
        return as_of, {k.upper(): Decimal(str(v)) for k, v in rates_raw.items()}
