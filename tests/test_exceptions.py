"""Tests for custom exception hierarchy.

Covers:
- BaseDomainException with error codes
- Exception subclasses
- Context preservation
"""

import pytest

from resilient_app.core import (
    DOMAIN_INTERNAL_ERROR,
    DOMAIN_VALIDATION_ERROR,
    BaseDomainException,
    FallbackError,
    InternalError,
    ResourceNotFoundError,
    TimeoutError,
    ValidationError,
)


class TestBaseDomainException:
    """Test base domain exception behavior."""

    def test_exception_requires_message_and_code(self):
        """BaseDomainException requires message and code."""
        exc = BaseDomainException(
            message="Something went wrong",
            code=DOMAIN_INTERNAL_ERROR,
        )

        assert exc.message == "Something went wrong"
        assert exc.code == DOMAIN_INTERNAL_ERROR

    def test_exception_str_format_includes_code(self):
        """String representation includes code and message."""
        exc = BaseDomainException(
            message="Validation failed",
            code=DOMAIN_VALIDATION_ERROR,
        )

        exc_str = str(exc)
        assert "[DOMAIN_VALIDATION_ERROR]" in exc_str
        assert "Validation failed" in exc_str

    def test_exception_includes_context(self):
        """Context dict is preserved and displayed."""
        exc = BaseDomainException(
            message="Operation failed",
            code=DOMAIN_INTERNAL_ERROR,
            context={"user_id": "123", "resource": "config"},
        )

        exc_str = str(exc)
        assert "user_id=123" in exc_str
        assert "resource=config" in exc_str
        assert exc.context == {"user_id": "123", "resource": "config"}

    def test_exception_preserves_cause(self):
        """Cause exception is preserved."""
        original = ValueError("Original error")

        exc = BaseDomainException(
            message="Wrapped error",
            code=DOMAIN_INTERNAL_ERROR,
            cause=original,
        )

        assert exc.cause is original

    def test_repr_format(self):
        """Repr shows class name, code, and message."""
        exc = BaseDomainException(
            message="Test",
            code="TEST_CODE",
        )

        repr_str = repr(exc)
        assert "BaseDomainException" in repr_str
        assert "TEST_CODE" in repr_str
        assert "Test" in repr_str


class TestExceptionSubclasses:
    """Test exception hierarchy subclasses."""

    def test_validation_error_inherits_base(self):
        """ValidationError is a BaseDomainException."""
        exc = ValidationError(
            message="Invalid input",
            code=DOMAIN_VALIDATION_ERROR,
        )

        assert isinstance(exc, BaseDomainException)
        assert isinstance(exc, ValidationError)

    def test_resource_not_found_error(self):
        """ResourceNotFoundError is properly typed."""
        exc = ResourceNotFoundError(
            message="File not found",
            code="TEST_NOT_FOUND",
        )

        assert isinstance(exc, BaseDomainException)
        assert isinstance(exc, ResourceNotFoundError)

    def test_timeout_error(self):
        """TimeoutError is properly typed."""
        exc = TimeoutError(
            message="Operation timed out",
            code="TEST_TIMEOUT",
        )

        assert isinstance(exc, BaseDomainException)
        assert isinstance(exc, TimeoutError)

    def test_internal_error(self):
        """InternalError is properly typed."""
        exc = InternalError(
            message="Unexpected error",
            code=DOMAIN_INTERNAL_ERROR,
        )

        assert isinstance(exc, BaseDomainException)
        assert isinstance(exc, InternalError)

    def test_fallback_error(self):
        """FallbackError is properly typed."""
        exc = FallbackError(
            message="All paths failed",
            code="TEST_FALLBACK",
        )

        assert isinstance(exc, BaseDomainException)
        assert isinstance(exc, FallbackError)
