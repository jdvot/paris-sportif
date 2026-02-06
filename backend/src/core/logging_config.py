"""Structured logging configuration using structlog.

Configures structlog to wrap Python's stdlib logging so that ALL existing
``logging.getLogger(__name__)`` calls automatically produce structured
JSON output in production and pretty console output in development.
"""

import logging
import logging.config
import uuid

import structlog


def setup_logging(json_output: bool = True, log_level: str = "INFO") -> None:
    """Configure structured logging for the entire application.

    Args:
        json_output: If True, output JSON (production). If False, pretty console (dev).
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    # Shared processors used by both structlog and stdlib logging.
    # NOTE: filter_by_level is NOT included here because it requires a real
    # structlog logger object, but foreign_pre_chain passes None for stdlib
    # log records, causing "AttributeError: 'NoneType' ... 'disabled'".
    # StackInfoRenderer is excluded to avoid verbose stack traces on every log.
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    # Configure structlog for direct structlog.get_logger() usage.
    # filter_by_level is safe here because structlog passes a real logger.
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to route through structlog's ProcessorFormatter.
    # This makes existing ``logging.getLogger(__name__).info(...)`` calls
    # produce structured output without changing any call sites.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quieten noisy third-party loggers
    for noisy_logger in ("uvicorn.access", "httpx", "httpcore", "apscheduler"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def generate_request_id() -> str:
    """Generate a short unique request ID."""
    return uuid.uuid4().hex[:12]
