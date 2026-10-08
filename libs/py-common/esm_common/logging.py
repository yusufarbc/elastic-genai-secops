"""Structured JSON logging shared by the Python services."""

from __future__ import annotations

import logging
import os

import structlog


def configure(service: str) -> structlog.stdlib.BoundLogger:
    level = logging.DEBUG if os.getenv("LOG_LEVEL") == "debug" else logging.INFO
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )
    structlog.contextvars.bind_contextvars(service=service)
    return structlog.get_logger()
