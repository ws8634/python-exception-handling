"""Fallback strategy implementation for graceful degradation.

Features:
- Primary path execution
- Fallback to secondary path on primary failure
- WARNING logging on fallback
- Proper exception propagation if both fail
"""

import logging
from typing import Any, Callable, Optional, TypeVar

from resilient_app.core import errors
from resilient_app.core.exceptions import BaseDomainException, FallbackError
from resilient_app.core.logging import get_logger, log_warning, log_error

T = TypeVar("T")


class FallbackStrategy:
    """Strategy for graceful degradation.

    When primary path fails, attempts secondary path.
    If both fail, propagates the last exception.

    Parameters:
        name: Unique name for this fallback strategy.
        primary: Primary function to execute.
        secondary: Secondary/fallback function to execute.
    """

    def __init__(
        self,
        name: str,
        primary: Optional[Callable[..., T]] = None,
        secondary: Optional[Callable[..., T]] = None,
    ):
        self.name = name
        self._primary = primary
        self._secondary = secondary
        self._logger = get_logger(f"fallback.{name}")

    def execute(self, *args: Any, **kwargs: Any) -> T:
        """Execute with fallback strategy.

        Args:
            *args: Positional arguments to pass to functions.
            **kwargs: Keyword arguments to pass to functions.

        Returns:
            Result from either primary or secondary path.

        Raises:
            FallbackError: If both primary and secondary paths fail.
            Exception: Any exception from secondary if primary failed
                       (wrapped in FallbackError if not already BaseDomainException).
        """
        primary_result: Optional[T] = None
        primary_exception: Optional[Exception] = None

        if self._primary:
            try:
                primary_result = self._primary(*args, **kwargs)
                return primary_result
            except Exception as e:
                primary_exception = e
                code = (
                    e.code
                    if isinstance(e, BaseDomainException)
                    else errors.FALLBACK_PRIMARY_FAILED
                )
                log_warning(
                    self._logger,
                    f"Primary path '{self.name}' failed, attempting fallback",
                    code=code,
                    context={"primary_error": str(e)},
                )

        if self._secondary:
            try:
                secondary_result = self._secondary(*args, **kwargs)
                log_warning(
                    self._logger,
                    f"Fallback path '{self.name}' succeeded",
                    code=errors.FALLBACK_SUCCESS,
                    context={
                        "primary_failed": primary_exception is not None,
                        "fallback_used": True,
                    },
                )
                return secondary_result
            except Exception as e:
                code = (
                    e.code
                    if isinstance(e, BaseDomainException)
                    else errors.FALLBACK_SECONDARY_FAILED
                )
                log_error(
                    self._logger,
                    f"Both primary and fallback paths '{self.name}' failed",
                    code=code,
                    context={
                        "primary_error": str(primary_exception) if primary_exception else None,
                        "secondary_error": str(e),
                    },
                    exc_info=True,
                )

                if isinstance(e, BaseDomainException):
                    raise
                else:
                    raise FallbackError(
                        message=f"Both paths failed for '{self.name}': {e}",
                        code=errors.FALLBACK_SECONDARY_FAILED,
                        cause=e,
                        context={
                            "primary_error": str(primary_exception) if primary_exception else None
                        },
                    ) from e

        if primary_exception:
            if isinstance(primary_exception, BaseDomainException):
                raise primary_exception
            else:
                raise FallbackError(
                    message=f"Primary path failed for '{self.name}': {primary_exception}",
                    code=errors.FALLBACK_PRIMARY_FAILED,
                    cause=primary_exception,
                ) from primary_exception

        raise FallbackError(
            message=f"No paths configured for '{self.name}'",
            code=errors.FALLBACK_SECONDARY_FAILED,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> T:
        """Callable interface."""
        return self.execute(*args, **kwargs)


def with_fallback(
    name: str, secondary: Callable[..., T]
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for fallback strategy.

    Usage:
        @with_fallback("my_operation", secondary_func)
        def primary_func(x):
            return x * 2

    Args:
        name: Name for this fallback strategy.
        secondary: Fallback function.

    Returns:
        Decorator that wraps the primary function.
    """

    def decorator(primary: Callable[..., T]) -> Callable[..., T]:
        strategy = FallbackStrategy(name=name, primary=primary, secondary=secondary)

        def wrapper(*args: Any, **kwargs: Any) -> T:
            return strategy.execute(*args, **kwargs)

        wrapper.__name__ = primary.__name__
        wrapper._strategy = strategy  # type: ignore
        return wrapper

    return decorator
