from __future__ import annotations

from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest
from redis import Redis

from app.bot.handlers import router
from app.bot.middlewares import DBSessionMiddleware, RedisMiddleware
from app.core.config import get_settings
from app.core.idempotency import IdempotencyStore
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(component="main")

app = FastAPI(title=settings.app_name)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
redis = Redis.from_url(settings.redis_url)

idempotency = IdempotencyStore(redis)

REQUEST_COUNT = Counter("assistant_requests_total", "Total webhook requests")
REQUEST_LATENCY = Histogram("assistant_request_latency_seconds", "Webhook latency")


dp.include_router(router)
dp.message.middleware(DBSessionMiddleware())
dp.message.middleware(RedisMiddleware(redis))
dp.callback_query.middleware(DBSessionMiddleware())
dp.callback_query.middleware(RedisMiddleware(redis))


@app.on_event("startup")
async def startup() -> None:
    webhook_url = f"{settings.webhook_url}/webhook/{settings.webhook_secret}"
    await bot.set_webhook(webhook_url)
    logger.info("webhook_set", url=webhook_url)


@app.on_event("shutdown")
async def shutdown() -> None:
    await bot.session.close()


@app.post("/webhook/{token}")
async def telegram_webhook(request: Request, token: str, x_telegram_bot_api_secret_token: str | None = Header(None)) -> dict[str, str]:
    REQUEST_COUNT.inc()
    if token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    if x_telegram_bot_api_secret_token and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    with REQUEST_LATENCY.time():
        payload = await request.json()
        update = Update.model_validate(payload)
        key = f"update:{update.update_id}"
        if idempotency.seen(key):
            return {"status": "duplicate"}
        idempotency.mark(key)
        await dp.feed_update(bot, update)
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Any:
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="disabled")
    return Response(generate_latest(), media_type="text/plain")
