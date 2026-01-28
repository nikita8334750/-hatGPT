from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(**context: Any) -> structlog.BoundLogger:
    return structlog.get_logger().bind(**context)
