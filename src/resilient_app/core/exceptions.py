"""Custom exception hierarchy for domain layer.

Domain layer only throws:
- BaseDomainException with error codes
- Few specialized subclasses
"""

from typing import Any, Optional


class BaseDomainException(Exception):
    """Base exception for all domain-level errors.
    
    All domain exceptions must include an error code.
    """

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.cause = cause
        self.context = context or {}

    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f" ({ctx_str})")
        return "".join(parts)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class ValidationError(BaseDomainException):
    """Raised when input validation fails in domain layer."""

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, cause, context)


class ResourceNotFoundError(BaseDomainException):
    """Raised when a required resource is not found."""

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, cause, context)


class TimeoutError(BaseDomainException):
    """Raised when an operation times out."""

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, cause, context)


class InternalError(BaseDomainException):
    """Raised when an unexpected internal error occurs."""

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, cause, context)


class CircuitBreakerError(BaseDomainException):
    """Raised when circuit breaker is open and rejects requests."""

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, cause, context)


class FallbackError(BaseDomainException):
    """Raised when both primary and fallback paths fail."""

    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, cause, context)
