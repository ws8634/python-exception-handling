"""Structured logging configuration.

Features:
- Single-line structured format
- Time, level, logger name, code (if present), message
- Extra context as key=value pairs
- DEBUG controlled by environment variable
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class StructuredFormatter(logging.Formatter):
    """Formatter for single-line structured logs.

    Format:
    <timestamp> <level> <logger> [<code>] <message> [key1=value1 key2=value2]
    """

    def format(self, record: logging.LogRecord) -> str:
        parts = []

        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        parts.append(timestamp)

        parts.append(record.levelname.upper())

        parts.append(record.name)

        code = getattr(record, "code", None)
        if code:
            parts.append(f"[code={code}]")

        parts.append(str(record.getMessage()))

        extra_context = getattr(record, "context", {})
        for key, value in sorted(extra_context.items()):
            parts.append(f"{key}={value}")

        if record.exc_info and record.levelno >= logging.ERROR:
            parts.append(self.formatException(record.exc_info))

        return " ".join(parts)

    def formatException(self, exc_info: tuple) -> str:
        import traceback

        lines = traceback.format_exception(*exc_info)
        return "\n" + "".join(lines).rstrip()


class ContextFilter(logging.Filter):
    """Filter to inject context into log records."""

    def __init__(self, code: Optional[str] = None, context: Optional[dict[str, Any]] = None):
        super().__init__()
        self._code = code
        self._context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "code") and self._code:
            record.code = self._code
        if not hasattr(record, "context") and self._context:
            record.context = self._context
        return True


_LOGGER_CACHE: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.

    Args:
        name: Logger name, typically __name__ of the module.

    Returns:
        Configured logger instance.
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    _LOGGER_CACHE[name] = logger
    return logger


def setup_logging(debug: bool = False) -> None:
    """Setup logging configuration.

    Args:
        debug: If True, enable DEBUG level output.
               Defaults to False, can be overridden by RESILIENT_DEBUG env var.
    """
    env_debug = os.environ.get("RESILIENT_DEBUG", "0").lower() in ("1", "true", "yes")
    effective_debug = debug or env_debug

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(StructuredFormatter())

    if effective_debug:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)

    root_logger.addHandler(console_handler)


def log_with_code(
    logger: logging.Logger,
    level: int,
    message: str,
    code: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    exc_info: bool = False,
) -> None:
    """Log a message with error code and context.

    Args:
        logger: Logger instance.
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        message: Log message.
        code: Error code (optional).
        context: Additional context as key-value pairs (optional).
        exc_info: Whether to include exception info (optional).
    """
    extra: dict[str, Any] = {}
    if code:
        extra["code"] = code
    if context:
        extra["context"] = context

    logger.log(level, message, extra=extra, exc_info=exc_info)


def log_debug(
    logger: logging.Logger,
    message: str,
    code: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> None:
    """Log at DEBUG level."""
    log_with_code(logger, logging.DEBUG, message, code, context)


def log_info(
    logger: logging.Logger,
    message: str,
    code: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> None:
    """Log at INFO level."""
    log_with_code(logger, logging.INFO, message, code, context)


def log_warning(
    logger: logging.Logger,
    message: str,
    code: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> None:
    """Log at WARNING level."""
    log_with_code(logger, logging.WARNING, message, code, context)


def log_error(
    logger: logging.Logger,
    message: str,
    code: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    exc_info: bool = False,
) -> None:
    """Log at ERROR level."""
    log_with_code(logger, logging.ERROR, message, code, context, exc_info)


def log_critical(
    logger: logging.Logger,
    message: str,
    code: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    exc_info: bool = False,
) -> None:
    """Log at CRITICAL level."""
    log_with_code(logger, logging.CRITICAL, message, code, context, exc_info)
