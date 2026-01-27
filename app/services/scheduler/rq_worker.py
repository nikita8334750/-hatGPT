from __future__ import annotations

from redis import Redis
from rq import Worker, Queue, Connection

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(component="rq_worker")


def main() -> None:
    redis = Redis.from_url(settings.redis_url)
    with Connection(redis):
        worker = Worker([Queue("scheduler")])
        logger.info("rq_worker_start")
        worker.work()


if __name__ == "__main__":
    main()
