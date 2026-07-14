"""Structured logging configuration.

Uses `structlog` layered on top of the standard library `logging` module
(rather than replacing it) specifically so that a later Azure Application
Insights integration (Milestone 12+) can attach its own `logging.Handler`
to the root logger and receive every log emitted through structlog, without
any call-site changes. This is the concrete mechanism behind the
observability strategy documented in `docs/architecture/observability.md`.

Usage
-----
    from app.core.logging import configure_logging, get_logger

    configure_logging(settings)  # called once, at startup
    logger = get_logger(__name__)
    logger.info("job_ingested", source="adzuna", job_id=str(job.id))

Log lines are structured key-value events (not free-form strings) so they
remain queryable once shipped to Application Insights / Azure Monitor.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structlog + stdlib logging for the current process.

    Renders logs as JSON in production/testing (machine-readable, ready to
    ship to Application Insights) and as a human-friendly console format in
    development (readable while iterating locally).
    """
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.debug:
        renderer: structlog.typing.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level],
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Keep stdlib logging (used by uvicorn, sqlalchemy, etc.) at the same
    # level so third-party library logs aren't silently dropped or overly
    # verbose relative to our own application logs.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to `name` (conventionally `__name__`)."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
