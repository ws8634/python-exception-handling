"""Demo scenarios implementation.

Each scenario demonstrates a specific resilience pattern.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from resilient_app.application.service import (
    AppResult,
    ExternalService,
    execute_with_logging,
)
from resilient_app.core import (
    CIRCUIT_OPEN,
    FALLBACK_PRIMARY_FAILED,
    FALLBACK_SECONDARY_FAILED,
    FALLBACK_SUCCESS,
    SUCCESS,
    CircuitBreaker,
    CircuitState,
    FallbackStrategy,
    get_logger,
    log_info,
)

logger = get_logger(__name__)


@dataclass
class DemoResult:
    """Result from a demo scenario.

    Attributes:
        name: Name of the scenario.
        operation_success: Whether the operation succeeded (from user perspective).
        expected_code: Expected error code for the scenario.
        actual_code: Actual error code from execution.
        message: Human-readable description.
        data: Optional result data.
    """

    name: str
    operation_success: bool
    expected_code: str
    actual_code: str
    message: str
    data: Optional[Any] = None

    @property
    def passed(self) -> bool:
        """Check if the scenario behaved as expected."""
        return self.actual_code == self.expected_code


def demo_normal() -> DemoResult:
    """Demo 1: Normal successful execution.

    Scenario:
    - Service call succeeds
    - Circuit breaker remains closed
    - Result returned successfully
    """
    log_info(logger, "=== DEMO 1: Normal Execution ===", code=SUCCESS)

    service = ExternalService("normal_service", success_count=10, fail_count=0)
    circuit = CircuitBreaker(
        name="demo_normal",
        window_size_seconds=60.0,
        failure_threshold=3,
        cooldown_seconds=10.0,
    )

    result = execute_with_logging(
        "demo_normal",
        lambda: circuit.execute(service),
    )

    return DemoResult(
        name="Normal Execution",
        operation_success=True,
        expected_code=SUCCESS,
        actual_code=result.code,
        message="Service call succeeded, circuit remains CLOSED",
        data=result.data,
    )


def demo_circuit_open() -> DemoResult:
    """Demo 2: Circuit breaker open.

    Scenario:
    - Service fails multiple times
    - Circuit opens after threshold
    - Next call is rejected immediately
    """
    log_info(logger, "=== DEMO 2: Circuit Breaker Open ===", code=CIRCUIT_OPEN)

    service = ExternalService("failing_service", success_count=0, fail_count=10)
    circuit = CircuitBreaker(
        name="demo_circuit",
        window_size_seconds=60.0,
        failure_threshold=2,
        cooldown_seconds=10.0,
    )

    for i in range(2):
        try:
            circuit.execute(service)
        except Exception:
            pass

    result = execute_with_logging(
        "demo_circuit_open",
        lambda: circuit.execute(service),
    )

    return DemoResult(
        name="Circuit Breaker Open",
        operation_success=False,
        expected_code=CIRCUIT_OPEN,
        actual_code=result.code,
        message="Circuit is OPEN, calls are rejected immediately",
        data={
            "circuit_state": circuit.state.value,
            "failures": circuit.metrics.failed_requests,
            "rejected": circuit.metrics.rejected_requests,
        },
    )


def demo_fallback_success() -> DemoResult:
    """Demo 3: Fallback success.

    Scenario:
    - Primary service fails
    - Fallback service succeeds
    - WARNING logged for fallback use
    - Result returned from fallback
    """
    log_info(logger, "=== DEMO 3: Fallback Success ===", code=FALLBACK_SUCCESS)

    def primary_func():
        raise ValueError("Primary service unavailable")

    def secondary_func():
        return "Fallback service result"

    fallback = FallbackStrategy(
        name="demo_fallback_success",
        primary=primary_func,
        secondary=secondary_func,
    )

    result = execute_with_logging(
        "demo_fallback_success",
        lambda: fallback.execute(),
    )

    return DemoResult(
        name="Fallback Success",
        operation_success=True,
        expected_code=SUCCESS,
        actual_code=result.code,
        message="Primary failed, fallback succeeded",
        data=result.data,
    )


def demo_fallback_failure() -> DemoResult:
    """Demo 4: Fallback failure.

    Scenario:
    - Primary service fails
    - Fallback service also fails
    - Error propagated with FALLBACK_SECONDARY_FAILED code
    """
    log_info(logger, "=== DEMO 4: Fallback Failure ===", code=FALLBACK_SECONDARY_FAILED)

    def primary_func():
        raise ValueError("Primary service unavailable")

    def secondary_func():
        raise ValueError("Secondary service also unavailable")

    fallback = FallbackStrategy(
        name="demo_fallback_failure",
        primary=primary_func,
        secondary=secondary_func,
    )

    result = execute_with_logging(
        "demo_fallback_failure",
        lambda: fallback.execute(),
    )

    return DemoResult(
        name="Fallback Failure",
        operation_success=False,
        expected_code=FALLBACK_SECONDARY_FAILED,
        actual_code=result.code,
        message="Both primary and fallback paths failed",
        data=None,
    )


def run_all_demos() -> list[DemoResult]:
    """Run all demo scenarios in sequence.

    Returns:
        List of results from each demo.
    """
    results = []

    results.append(demo_normal())
    results.append(demo_circuit_open())
    results.append(demo_fallback_success())
    results.append(demo_fallback_failure())

    return results
