"""Application service layer.

This layer:
- Orchestrates domain operations
- Collects domain exceptions
- Logs full stack traces (via logging)
- Does NOT print traceback to stdout/stderr
"""

from dataclasses import dataclass
from typing import Any, Optional

from resilient_app.core import (
    APPLICATION_ORCHESTRATION_ERROR,
    CIRCUIT_OPEN,
    DOMAIN_INTERNAL_ERROR,
    DOMAIN_VALIDATION_ERROR,
    FALLBACK_SECONDARY_FAILED,
    SUCCESS,
    BaseDomainException,
    CircuitBreaker,
    FallbackStrategy,
    FallbackError,
    InternalError,
    ValidationError,
    get_logger,
    log_error,
    log_info,
)

logger = get_logger(__name__)


@dataclass
class AppResult:
    """Stable result format from application layer.

    Attributes:
        success: Whether the operation succeeded.
        code: Error code (or SUCCESS).
        message: Human-readable message.
        data: Optional result data on success.
    """

    success: bool
    code: str
    message: str
    data: Optional[Any] = None


class ApplicationError(BaseDomainException):
    """Stable exception type for application layer.

    This is what gets presented to CLI layer.
    """

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, cause, context)


class ExternalServiceError(ApplicationError):
    """Error from external service call."""

    pass


class ExternalService:
    """Simulated external service for demonstration.

    Can be configured to:
    - Always succeed
    - Always fail
    - Succeed/fail based on call count
    """

    def __init__(
        self,
        name: str,
        success_count: int = 0,
        fail_count: int = 0,
        always_fail: bool = False,
    ):
        self.name = name
        self._success_count = success_count
        self._fail_count = fail_count
        self._always_fail = always_fail
        self._call_count: int = 0
        self._logger = get_logger(f"service.{name}")

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        """Call the service."""
        return self.execute(*args, **kwargs)

    def execute(self, *args: Any, **kwargs: Any) -> str:
        """Execute the service call.

        Returns:
            Success message on success.

        Raises:
            ExternalServiceError: On configured failure.
            BaseDomainException: Other domain exceptions.
        """
        self._call_count += 1

        if self._always_fail:
            error = ExternalServiceError(
                message=f"Service '{self.name}' is configured to always fail",
                code=DOMAIN_INTERNAL_ERROR,
                context={"call_count": self._call_count},
            )
            log_error(
                self._logger,
                f"Service '{self.name}' failed on call {self._call_count}",
                code=error.code,
                exc_info=False,
            )
            raise error

        if self._call_count <= self._success_count:
            log_info(
                self._logger,
                f"Service '{self.name}' succeeded on call {self._call_count}",
                code=SUCCESS,
                context={"call_count": self._call_count},
            )
            return f"Service '{self.name}' call {self._call_count} succeeded"

        if self._call_count <= self._success_count + self._fail_count:
            error = ExternalServiceError(
                message=f"Service '{self.name}' failed on call {self._call_count}",
                code=DOMAIN_INTERNAL_ERROR,
                context={"call_count": self._call_count},
            )
            log_error(
                self._logger,
                f"Service '{self.name}' failed on call {self._call_count}",
                code=error.code,
                exc_info=False,
            )
            raise error

        log_info(
            self._logger,
            f"Service '{self.name}' succeeded on call {self._call_count}",
            code=SUCCESS,
            context={"call_count": self._call_count},
        )
        return f"Service '{self.name}' call {self._call_count} succeeded"

    def reset(self) -> None:
        """Reset call counter."""
        self._call_count = 0


def wrap_domain_exception(exc: Exception) -> ApplicationError:
    """Wrap a domain exception into a stable ApplicationError.

    Args:
        exc: Any exception (typically BaseDomainException).

    Returns:
        ApplicationError with preserved code and message.
    """
    if isinstance(exc, ApplicationError):
        return exc

    if isinstance(exc, BaseDomainException):
        return ApplicationError(
            message=exc.message,
            code=exc.code,
            cause=exc,
            context=exc.context,
        )

    return ApplicationError(
        message=str(exc),
        code=APPLICATION_ORCHESTRATION_ERROR,
        cause=exc,
    )


def execute_with_logging(
    operation_name: str,
    func,
    *args: Any,
    **kwargs: Any,
) -> AppResult:
    """Execute a function with proper exception handling and logging.

    This demonstrates the orchestration layer pattern:
    - Try to execute function
    - Catch domain exceptions
    - Log full stack trace (for debugging)
    - Return stable AppResult (for CLI)

    Args:
        operation_name: Name for logging.
        func: Function to execute.
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Returns:
        AppResult with success/error info.
    """
    try:
        result = func(*args, **kwargs)
        return AppResult(
            success=True,
            code=SUCCESS,
            message=f"{operation_name} completed successfully",
            data=result,
        )
    except BaseDomainException as exc:
        log_error(
            logger,
            f"Domain error in {operation_name}: {exc.message}",
            code=exc.code,
            context=exc.context,
            exc_info=True,
        )
        return AppResult(
            success=False,
            code=exc.code,
            message=exc.message,
            data=None,
        )
    except Exception as exc:
        wrapped = wrap_domain_exception(exc)
        log_error(
            logger,
            f"Unexpected error in {operation_name}: {wrapped.message}",
            code=wrapped.code,
            exc_info=True,
        )
        return AppResult(
            success=False,
            code=wrapped.code,
            message=wrapped.message,
            data=None,
        )
