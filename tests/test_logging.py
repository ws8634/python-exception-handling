"""Tests for logging module.

Covers:
- Structured formatting
- Log levels
- Code and context injection
- Environment variable control
"""

import io
import logging
import os
import re
from unittest import mock

import pytest

from resilient_app.core import (
    DOMAIN_VALIDATION_ERROR,
    SUCCESS,
    StructuredFormatter,
    get_logger,
    log_debug,
    log_error,
    log_info,
    log_warning,
    log_with_code,
    setup_logging,
)


class TestStructuredFormatter:
    """Test structured log formatting."""

    def test_format_with_exc_info_is_single_line(self):
        """ERROR level with exc_info produces single-line output with escaped stack.

        The first line (and the only line for the log record) must:
        - Be a single line (no visible newlines)
        - Contain the code field if present
        - Include stack information as escaped string in 'stack=' field
        """
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error occurred",
            args=None,
            exc_info=exc_info,
        )
        record.code = DOMAIN_VALIDATION_ERROR

        formatted = formatter.format(record)

        lines = formatted.split("\n")
        assert len(lines) == 1, f"Expected single line, got {len(lines)} lines: {formatted}"

        assert "[code=DOMAIN_VALIDATION_ERROR]" in formatted, "Code field should be present"
        assert "stack=" in formatted, "Stack field should be present as escaped string"

        assert "\\n" in formatted, "Newlines should be escaped as literal \\n"
        assert "ValueError" in formatted, "Exception type should be in stack"
        assert "Test exception" in formatted, "Exception message should be in stack"

    def test_format_includes_timestamp_level_logger(self):
        """Basic log format includes timestamp, level, logger."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=None,
            exc_info=None,
        )

        formatted = formatter.format(record)

        parts = formatted.split()
        assert len(parts) >= 3
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", parts[0])
        assert parts[1] == "INFO"
        assert parts[2] == "test_logger"
        assert "Test message" in formatted

    def test_format_includes_code_when_present(self):
        """Log format includes code when set on record."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Something went wrong",
            args=None,
            exc_info=None,
        )
        record.code = DOMAIN_VALIDATION_ERROR

        formatted = formatter.format(record)

        assert "[code=DOMAIN_VALIDATION_ERROR]" in formatted

    def test_format_includes_context_key_value_pairs(self):
        """Log format includes context as key=value pairs."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Warning message",
            args=None,
            exc_info=None,
        )
        record.context = {"user_id": "123", "request_id": "abc-xyz"}

        formatted = formatter.format(record)

        assert "user_id=123" in formatted
        assert "request_id=abc-xyz" in formatted


class TestLoggingFunctions:
    """Test convenience logging functions."""

    def setup_method(self):
        """Reset logging state before each test."""
        self.captured_output = io.StringIO()
        self.handler = logging.StreamHandler(self.captured_output)
        self.handler.setFormatter(StructuredFormatter())

        self.root_logger = logging.getLogger()
        for h in list(self.root_logger.handlers):
            self.root_logger.removeHandler(h)
        self.root_logger.addHandler(self.handler)
        self.root_logger.setLevel(logging.DEBUG)

    def get_output(self) -> str:
        """Get captured output."""
        self.handler.flush()
        return self.captured_output.getvalue()

    def test_log_with_code_adds_code(self):
        """log_with_code adds code to the log record."""
        logger = get_logger("test_code_log")

        log_with_code(
            logger,
            logging.ERROR,
            "Error occurred",
            code=DOMAIN_VALIDATION_ERROR,
        )

        output = self.get_output()
        assert "[code=DOMAIN_VALIDATION_ERROR]" in output
        assert "Error occurred" in output

    def test_log_with_code_adds_context(self):
        """log_with_code adds context key=value pairs."""
        logger = get_logger("test_ctx_log")

        log_with_code(
            logger,
            logging.WARNING,
            "Warning",
            context={"foo": "bar", "count": 42},
        )

        output = self.get_output()
        assert "foo=bar" in output
        assert "count=42" in output

    def test_log_level_functions(self):
        """Convenience functions log at correct levels."""
        logger = get_logger("test_levels")

        log_debug(logger, "Debug message")
        log_info(logger, "Info message")
        log_warning(logger, "Warning message")
        log_error(logger, "Error message")

        output = self.get_output()
        lines = output.strip().split("\n")

        assert len(lines) == 4
        assert " DEBUG " in lines[0]
        assert " INFO " in lines[1]
        assert " WARNING " in lines[2]
        assert " ERROR " in lines[3]


class TestSetupLogging:
    """Test logging setup configuration."""

    def teardown_method(self):
        """Clean up environment after tests."""
        if "RESILIENT_DEBUG" in os.environ:
            del os.environ["RESILIENT_DEBUG"]

    def test_setup_logging_default_level_is_info(self):
        """Without debug flag, handler level is INFO."""
        setup_logging(debug=False)

        root = logging.getLogger()
        assert len(root.handlers) >= 1

        handler = root.handlers[0]
        assert handler.level == logging.INFO

    def test_setup_logging_with_debug_flag(self):
        """With debug=True, handler level is DEBUG."""
        setup_logging(debug=True)

        root = logging.getLogger()
        handler = root.handlers[0]
        assert handler.level == logging.DEBUG

    def test_setup_logging_with_env_var(self):
        """With RESILIENT_DEBUG=1, handler level is DEBUG."""
        os.environ["RESILIENT_DEBUG"] = "1"

        try:
            setup_logging(debug=False)

            root = logging.getLogger()
            handler = root.handlers[0]
            assert handler.level == logging.DEBUG
        finally:
            del os.environ["RESILIENT_DEBUG"]

    def test_setup_logging_env_var_false(self):
        """With RESILIENT_DEBUG=0, handler level is INFO."""
        os.environ["RESILIENT_DEBUG"] = "0"

        try:
            setup_logging(debug=False)

            root = logging.getLogger()
            handler = root.handlers[0]
            assert handler.level == logging.INFO
        finally:
            del os.environ["RESILIENT_DEBUG"]


class TestGetLogger:
    """Test logger caching."""

    def test_get_logger_caches_instances(self):
        """Same name returns same logger instance."""
        logger1 = get_logger("cached_logger")
        logger2 = get_logger("cached_logger")

        assert logger1 is logger2

    def test_get_logger_different_names_different_loggers(self):
        """Different names return different loggers."""
        logger1 = get_logger("logger_a")
        logger2 = get_logger("logger_b")

        assert logger1 is not logger2
        assert logger1.name == "logger_a"
        assert logger2.name == "logger_b"
