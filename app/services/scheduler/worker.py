from __future__ import annotations

import time

from redis import Redis

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.scheduler.tick_worker import enqueue_tick

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(component="scheduler_worker")


def main() -> None:
    redis = Redis.from_url(settings.redis_url)
    while True:
        enqueue_tick(redis)
        logger.info("tick_enqueued")
        time.sleep(30)


if __name__ == "__main__":
    main()
