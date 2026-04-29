"""Core modules for the resilient application.

This package provides:
- Error code definitions
- Custom exception hierarchy
- Structured logging
- Circuit breaker pattern
- Fallback strategy
"""

from resilient_app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitMetrics,
    CircuitState,
    SlidingWindow,
)
from resilient_app.core.errors import (
    APPLICATION_ORCHESTRATION_ERROR,
    APPLICATION_SERVICE_ERROR,
    CIRCUIT_HALF_OPEN,
    CIRCUIT_OPEN,
    CIRCUIT_RECOVERED,
    CLI_ARGUMENT_ERROR,
    CLI_EXECUTION_ERROR,
    DOMAIN_INTERNAL_ERROR,
    DOMAIN_RESOURCE_NOT_FOUND,
    DOMAIN_TIMEOUT_ERROR,
    DOMAIN_VALIDATION_ERROR,
    FALLBACK_PRIMARY_FAILED,
    FALLBACK_SECONDARY_FAILED,
    FALLBACK_SUCCESS,
    SUCCESS,
)
from resilient_app.core.exceptions import (
    BaseDomainException,
    CircuitBreakerError,
    FallbackError,
    InternalError,
    ResourceNotFoundError,
    TimeoutError,
    ValidationError,
)
from resilient_app.core.fallback import FallbackStrategy, with_fallback
from resilient_app.core.logging import (
    ContextFilter,
    StructuredFormatter,
    get_logger,
    log_critical,
    log_debug,
    log_error,
    log_info,
    log_warning,
    log_with_code,
    setup_logging,
)

__all__ = [
    "CircuitBreaker",
    "CircuitMetrics",
    "CircuitState",
    "SlidingWindow",
    "APPLICATION_ORCHESTRATION_ERROR",
    "APPLICATION_SERVICE_ERROR",
    "CIRCUIT_HALF_OPEN",
    "CIRCUIT_OPEN",
    "CIRCUIT_RECOVERED",
    "CLI_ARGUMENT_ERROR",
    "CLI_EXECUTION_ERROR",
    "DOMAIN_INTERNAL_ERROR",
    "DOMAIN_RESOURCE_NOT_FOUND",
    "DOMAIN_TIMEOUT_ERROR",
    "DOMAIN_VALIDATION_ERROR",
    "FALLBACK_PRIMARY_FAILED",
    "FALLBACK_SECONDARY_FAILED",
    "FALLBACK_SUCCESS",
    "SUCCESS",
    "BaseDomainException",
    "CircuitBreakerError",
    "FallbackError",
    "InternalError",
    "ResourceNotFoundError",
    "TimeoutError",
    "ValidationError",
    "FallbackStrategy",
    "with_fallback",
    "ContextFilter",
    "StructuredFormatter",
    "get_logger",
    "log_critical",
    "log_debug",
    "log_error",
    "log_info",
    "log_warning",
    "log_with_code",
    "setup_logging",
]
