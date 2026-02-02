# Telegram Currency Converter Bot

A Telegram bot that provides currency conversion with near-real-time updates, provider failover, watch alerts, and optional history storage.

## Features
- Background rate updates every `UPDATE_INTERVAL_SECONDS` (default 60).
- Redis cache for rate snapshots and health info.
- Provider failover with circuit breaker.
- Commands: `/rate`, `/convert`, `/status`, `/base`, `/precision`, `/watch`, `/watchlist`, `/unwatch`, `/history`.
- Optional Postgres history storage (requires `asyncpg`).

## Environment variables
| Variable | Description | Default |
| --- | --- | --- |
| `BOT_TOKEN` | Telegram bot token | **required** |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `PROVIDER_URL` | Provider A endpoint | `https://api.example.com/latest` |
| `RATES_API_KEY` | Provider A API key | empty |
| `UPDATE_INTERVAL_SECONDS` | Background update interval | `60` |
| `DEFAULT_BASE` | Default base currency | `USD` |
| `MAX_STALENESS_SECONDS` | Staleness warning threshold | `3600` |
| `WATCH_COOLDOWN_SECONDS` | Watch notification cooldown | `300` |
| `RATE_LIMIT_SECONDS` | Per-chat command rate limit | `2` |
| `ENABLE_HISTORY` | Enable Postgres history | `false` |
| `POSTGRES_DSN` | Postgres connection string | empty |

## Running locally
```bash
export BOT_TOKEN=your_token
export RATES_API_KEY=your_key
export PROVIDER_URL=https://api.example.com/latest

docker-compose up --build
```

To enable history:
```bash
export ENABLE_HISTORY=true
export POSTGRES_DSN=postgresql://bot:bot@postgres:5432/rates

docker-compose --profile history up --build
```

## Commands
- `/rate EURUSD` or `/rate EUR USD`
- `/convert 100 usd eur`
- `/status`
- `/base USD`
- `/precision 2|4|6`
- `/watch USD EUR 1.1` or `/watch USD EUR 2%`
- `/watchlist`
- `/unwatch <id>`
- `/history USD EUR 24h`

## Tests
```bash
pytest
```
