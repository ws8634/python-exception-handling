"""Circuit breaker implementation for resilient execution.

Features:
- Sliding window failure counting
- Open state with short-circuit rejection
- Cooldown period before half-open state
- Probe request in half-open state
- Logging with specialized subcodes
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from resilient_app.core import errors
from resilient_app.core.exceptions import CircuitBreakerError
from resilient_app.core.logging import get_logger, log_warning, log_info

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker."""

    total_requests: int = 0
    failed_requests: int = 0
    successful_requests: int = 0
    rejected_requests: int = 0
    state_changes: int = 0


@dataclass
class SlidingWindow:
    """Sliding window for failure tracking."""

    window_size_seconds: float
    threshold: int
    failures: list[tuple[float, Exception]] = field(default_factory=list)

    def record_failure(self, exception: Exception) -> None:
        """Record a failure at current time."""
        self.failures.append((time.monotonic(), exception))

    def get_failure_count(self) -> int:
        """Get number of failures within the sliding window."""
        now = time.monotonic()
        cutoff = now - self.window_size_seconds
        self.failures = [(t, e) for t, e in self.failures if t >= cutoff]
        return len(self.failures)

    def is_threshold_exceeded(self) -> bool:
        """Check if failure count exceeds threshold."""
        return self.get_failure_count() >= self.threshold

    def reset(self) -> None:
        """Reset the failure window."""
        self.failures.clear()


class CircuitBreaker:
    """Circuit breaker for wrapping potentially failing calls.

    Parameters:
        name: Unique name for this circuit breaker.
        window_size_seconds: Size of the sliding window for failure counting.
        failure_threshold: Number of failures to trigger circuit open.
        cooldown_seconds: Time to wait before allowing half-open probe.
        half_open_success_threshold: Number of successful probes needed to close.

    States:
        CLOSED: Normal operation, all requests pass through.
        OPEN: Circuit is open, requests are rejected immediately.
        HALF_OPEN: Probing state, limited requests allowed to test recovery.
    """

    def __init__(
        self,
        name: str,
        window_size_seconds: float = 10.0,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        half_open_success_threshold: int = 3,
    ):
        self.name = name
        self.window_size_seconds = window_size_seconds
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._open_at: Optional[float] = None
        self._sliding_window = SlidingWindow(
            window_size_seconds=window_size_seconds,
            threshold=failure_threshold,
        )
        self._metrics = CircuitMetrics()
        self._half_open_success_count: int = 0
        self._logger = get_logger(f"circuit_breaker.{name}")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def metrics(self) -> CircuitMetrics:
        """Get circuit breaker metrics."""
        return self._metrics

    def _should_allow_request(self) -> bool:
        """Check if a request should be allowed to pass through.

        Handles state transitions based on timing.
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            if self._open_at is None:
                self._state = CircuitState.CLOSED
                return True

            now = time.monotonic()
            if now - self._open_at >= self.cooldown_seconds:
                self._transition_to_half_open()
                return True

            self._metrics.rejected_requests += 1
            return False

        if self._state == CircuitState.HALF_OPEN:
            return True

        return False

    def _transition_to_open(self, cause: Exception) -> None:
        """Transition circuit from CLOSED to OPEN state."""
        previous = self._state
        self._state = CircuitState.OPEN
        self._open_at = time.monotonic()
        self._metrics.state_changes += 1

        log_warning(
            self._logger,
            f"Circuit breaker '{self.name}' opened due to failure threshold exceeded",
            code=errors.CIRCUIT_OPEN,
            context={
                "previous_state": previous.value,
                "failures": self._sliding_window.get_failure_count(),
                "threshold": self.failure_threshold,
            },
        )

    def _transition_to_half_open(self) -> None:
        """Transition circuit from OPEN to HALF_OPEN state."""
        previous = self._state
        self._state = CircuitState.HALF_OPEN
        self._half_open_success_count = 0
        self._metrics.state_changes += 1

        log_info(
            self._logger,
            f"Circuit breaker '{self.name}' entering half-open state after cooldown",
            code=errors.CIRCUIT_HALF_OPEN,
            context={
                "previous_state": previous.value,
                "cooldown_seconds": self.cooldown_seconds,
            },
        )

    def _transition_to_closed(self) -> None:
        """Transition circuit from HALF_OPEN to CLOSED state."""
        previous = self._state
        self._state = CircuitState.CLOSED
        self._sliding_window.reset()
        self._half_open_success_count = 0
        self._metrics.state_changes += 1

        log_info(
            self._logger,
            f"Circuit breaker '{self.name}' recovered and closed",
            code=errors.CIRCUIT_RECOVERED,
            context={
                "previous_state": previous.value,
                "successful_probes": self.half_open_success_threshold,
            },
        )

    def _record_success(self) -> None:
        """Record a successful call."""
        self._metrics.total_requests += 1
        self._metrics.successful_requests += 1

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.half_open_success_threshold:
                self._transition_to_closed()

    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        self._metrics.total_requests += 1
        self._metrics.failed_requests += 1

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count = 0
            self._transition_to_open(exception)
            return

        if self._state == CircuitState.CLOSED:
            self._sliding_window.record_failure(exception)
            if self._sliding_window.is_threshold_exceeded():
                self._transition_to_open(exception)

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            func: Function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func if successful.

        Raises:
            CircuitBreakerError: If circuit is open.
            Exception: Any exception raised by func (after recording failure).
        """
        if not self._should_allow_request():
            raise CircuitBreakerError(
                message=f"Circuit breaker '{self.name}' is OPEN, rejecting request",
                code=errors.CIRCUIT_OPEN,
                context={
                    "state": self._state.value,
                    "cooldown_remaining": max(
                        0.0,
                        (self._open_at or 0) + self.cooldown_seconds - time.monotonic(),
                    )
                    if self._open_at
                    else 0.0,
                },
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator interface for circuit breaker."""

        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.execute(func, *args, **kwargs)

        wrapper.__name__ = func.__name__
        return wrapper

    def reset(self) -> None:
        """Reset circuit breaker to initial state.

        Useful for testing.
        """
        self._state = CircuitState.CLOSED
        self._open_at = None
        self._sliding_window.reset()
        self._half_open_success_count = 0
        self._metrics = CircuitMetrics()
