import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 5.0,
    retries: int = 3,
    backoff_base: float = 0.5,
) -> httpx.Response:
    """Make HTTP request with exponential backoff retry logic."""
    delay = backoff_base
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
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
            return response
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as exc:
            last_exc = exc
            logger.warning("HTTP request failed (attempt %d/%d): %s", attempt + 1, retries, exc)
            if attempt == retries - 1:
                break
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    raise httpx.HTTPError(f"HTTP request failed after {retries} attempts") from last_exc
