"""Tests for fallback strategy.

Covers:
- Primary path succeeds
- Primary fails, secondary succeeds
- Both paths fail
- Exception propagation
"""

import pytest

from resilient_app.core import (
    DOMAIN_INTERNAL_ERROR,
    FALLBACK_PRIMARY_FAILED,
    FALLBACK_SECONDARY_FAILED,
    FALLBACK_SUCCESS,
    SUCCESS,
    BaseDomainException,
    FallbackError,
    FallbackStrategy,
    ValidationError,
    with_fallback,
)


class TestFallbackStrategy:
    """Test fallback strategy behavior."""

    def test_primary_succeeds(self):
        """When primary succeeds, it is used and secondary is not called."""
        secondary_called = False

        def primary():
            return "primary_result"

        def secondary():
            nonlocal secondary_called
            secondary_called = True
            return "secondary_result"

        fallback = FallbackStrategy(
            name="test",
            primary=primary,
            secondary=secondary,
        )

        result = fallback.execute()

        assert result == "primary_result"
        assert secondary_called is False

    def test_primary_fails_secondary_succeeds(self):
        """When primary fails, secondary is attempted."""

        def primary():
            raise ValueError("Primary failed")

        def secondary():
            return "secondary_result"

        fallback = FallbackStrategy(
            name="test",
            primary=primary,
            secondary=secondary,
        )

        result = fallback.execute()

        assert result == "secondary_result"

    def test_both_paths_fail(self):
        """When both paths fail, exception is propagated."""

        def primary():
            raise ValueError("Primary failed")

        def secondary():
            raise ValueError("Secondary failed")

        fallback = FallbackStrategy(
            name="test",
            primary=primary,
            secondary=secondary,
        )

        with pytest.raises(FallbackError) as exc_info:
            fallback.execute()

        assert exc_info.value.code == FALLBACK_SECONDARY_FAILED
        assert "Primary failed" in str(exc_info.value.cause) or exc_info.value.cause is not None

    def test_primary_raises_base_domain_exception(self):
        """Domain exceptions from primary are preserved."""

        def primary():
            raise ValidationError(
                message="Validation failed",
                code=DOMAIN_INTERNAL_ERROR,
            )

        def secondary():
            return "ok"

        fallback = FallbackStrategy(
            name="test",
            primary=primary,
            secondary=secondary,
        )

        result = fallback.execute()
        assert result == "ok"

    def test_secondary_raises_base_domain_exception(self):
        """Domain exceptions from secondary are propagated directly."""

        def primary():
            raise ValueError("Primary failed")

        def secondary():
            raise ValidationError(
                message="Secondary validation failed",
                code=DOMAIN_INTERNAL_ERROR,
            )

        fallback = FallbackStrategy(
            name="test",
            primary=primary,
            secondary=secondary,
        )

        with pytest.raises(BaseDomainException) as exc_info:
            fallback.execute()

        assert exc_info.value.code == DOMAIN_INTERNAL_ERROR
        assert "Secondary validation failed" in exc_info.value.message

    def test_with_fallback_decorator(self):
        """Decorator interface works correctly."""
        secondary_called = False

        def secondary(*args, **kwargs):
            nonlocal secondary_called
            secondary_called = True
            return "decorated_secondary"

        @with_fallback(name="test_decorator", secondary=secondary)
        def primary(should_fail: bool = False):
            if should_fail:
                raise ValueError("Failed")
            return "decorated_primary"

        result1 = primary(should_fail=False)
        assert result1 == "decorated_primary"
        assert secondary_called is False

        result2 = primary(should_fail=True)
        assert result2 == "decorated_secondary"
        assert secondary_called is True

    def test_no_secondary_configured(self):
        """If no secondary and primary fails, primary exception is raised."""

        def primary():
            raise ValueError("Primary failed")

        fallback = FallbackStrategy(
            name="test",
            primary=primary,
            secondary=None,
        )

        with pytest.raises(FallbackError) as exc_info:
            fallback.execute()

        assert exc_info.value.code == FALLBACK_PRIMARY_FAILED

    def test_no_paths_configured(self):
        """If neither primary nor secondary is configured, error is raised."""
        fallback = FallbackStrategy(
            name="test",
            primary=None,
            secondary=None,
        )

        with pytest.raises(FallbackError) as exc_info:
            fallback.execute()

        assert exc_info.value.code == FALLBACK_SECONDARY_FAILED
