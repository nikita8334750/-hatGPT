from dataclasses import dataclass
from datetime import datetime, timedelta

from app.storage.redis_store import RatesSnapshot


@dataclass
class HistoryConfig:
    dsn: str


class HistoryWriter:
    def __init__(self, config: HistoryConfig):
        self._config = config
        self._pool = None

    async def connect(self) -> None:
        try:
            import asyncpg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("asyncpg is required for history support") from exc

        self._pool = await asyncpg.create_pool(self._config.dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rates_history (
                    id serial primary key,
                    base text,
                    quote text,
                    rate numeric,
                    as_of timestamptz,
                    provider text,
                    fetched_at timestamptz
                )
                """
            )

    async def write_snapshot(self, snapshot: RatesSnapshot) -> None:
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            for quote, rate in snapshot.rates.items():
                await conn.execute(
                    """
                    INSERT INTO rates_history (base, quote, rate, as_of, provider, fetched_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    snapshot.base,
                    quote,
                    rate,
                    snapshot.as_of,
                    snapshot.provider,
                    snapshot.fetched_at,
                )

    async def get_history(self, base: str, quote: str, window: str) -> list[tuple[str, str, str]]:
        if not self._pool:
            return []
        delta = timedelta(hours=24) if window == "24h" else timedelta(days=7)
        since = datetime.utcnow() - delta
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT rate, as_of
                FROM rates_history
                WHERE base=$1 AND quote=$2 AND as_of >= $3
                ORDER BY as_of DESC
                LIMIT 10
                """,
                base,
                quote,
                since,
            )
        return [(str(row["rate"]), row["as_of"].isoformat()) for row in rows]
