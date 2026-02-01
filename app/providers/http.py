import asyncio
from typing import Any

import httpx


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 5.0,
    retries: int = 3,
) -> httpx.Response:
    delay = 0.5
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt == retries - 1:
                break
            await asyncio.sleep(delay)
            delay *= 2
    raise httpx.HTTPError("HTTP request failed") from last_exc
