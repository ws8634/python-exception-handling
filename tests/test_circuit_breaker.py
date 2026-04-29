"""Tests for circuit breaker pattern.

Covers:
- Circuit opens on failure threshold
- Circuit rejects requests when open
- Circuit transitions to half-open after cooldown
- Circuit recovers (closes) on successful probes
- Circuit re-opens on half-open failure
"""

import time
from unittest import mock

import pytest

from resilient_app.core import (
    CIRCUIT_HALF_OPEN,
    CIRCUIT_OPEN,
    CIRCUIT_RECOVERED,
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
)


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """Circuit breaker starts in CLOSED state."""
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=10.0,
            failure_threshold=3,
            cooldown_seconds=30.0,
        )
        assert circuit.state == CircuitState.CLOSED

    def test_circuit_opens_when_threshold_exceeded(self):
        """Circuit opens after failure threshold is exceeded."""
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=60.0,
            failure_threshold=2,
            cooldown_seconds=10.0,
        )

        def failing_func():
            raise ValueError("Simulated failure")

        for _ in range(2):
            with pytest.raises(ValueError):
                circuit.execute(failing_func)

        assert circuit.state == CircuitState.OPEN
        assert circuit.metrics.failed_requests == 2

    def test_circuit_rejects_requests_when_open(self):
        """Open circuit immediately rejects requests."""
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=60.0,
            failure_threshold=1,
            cooldown_seconds=10.0,
        )

        def failing_func():
            raise ValueError("Simulated failure")

        with pytest.raises(ValueError):
            circuit.execute(failing_func)

        assert circuit.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerError) as exc_info:
            circuit.execute(lambda: "should not be called")

        assert exc_info.value.code == CIRCUIT_OPEN
        assert circuit.metrics.rejected_requests == 1

    def test_circuit_transitions_to_half_open_after_cooldown(self):
        """Circuit transitions to HALF_OPEN after cooldown period.

        Uses mock time to simulate cooldown passage.
        """
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=60.0,
            failure_threshold=1,
            cooldown_seconds=5.0,
        )

        base_time = time.monotonic()

        def failing_func():
            raise ValueError("Simulated failure")

        with mock.patch("time.monotonic", return_value=base_time):
            with pytest.raises(ValueError):
                circuit.execute(failing_func)
            assert circuit.state == CircuitState.OPEN

        with mock.patch("time.monotonic", return_value=base_time + 1.0):
            with pytest.raises(CircuitBreakerError):
                circuit.execute(lambda: "nope")
            assert circuit.state == CircuitState.OPEN

        with mock.patch("time.monotonic", return_value=base_time + 6.0):
            success = False
            try:
                result = circuit.execute(lambda: "allowed now")
                assert result == "allowed now"
                success = True
            except CircuitBreakerError:
                pass

            assert success, "Circuit should allow request after cooldown"
            assert circuit.state == CircuitState.HALF_OPEN

    def test_circuit_closes_after_successful_half_open_probes(self):
        """Circuit closes after enough successful probes in half-open."""
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=60.0,
            failure_threshold=1,
            cooldown_seconds=5.0,
            half_open_success_threshold=2,
        )

        base_time = time.monotonic()

        def failing_func():
            raise ValueError("Simulated failure")

        with mock.patch("time.monotonic", return_value=base_time):
            with pytest.raises(ValueError):
                circuit.execute(failing_func)
            assert circuit.state == CircuitState.OPEN

        with mock.patch("time.monotonic", return_value=base_time + 10.0):
            circuit.execute(lambda: "probe 1")
            assert circuit.state == CircuitState.HALF_OPEN

            circuit.execute(lambda: "probe 2")
            assert circuit.state == CircuitState.CLOSED

    def test_circuit_reopens_on_half_open_failure(self):
        """Circuit re-opens if a half-open probe fails."""
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=60.0,
            failure_threshold=1,
            cooldown_seconds=5.0,
            half_open_success_threshold=3,
        )

        base_time = time.monotonic()

        def failing_func():
            raise ValueError("Simulated failure")

        with mock.patch("time.monotonic", return_value=base_time):
            with pytest.raises(ValueError):
                circuit.execute(failing_func)
            assert circuit.state == CircuitState.OPEN

        with mock.patch("time.monotonic", return_value=base_time + 10.0):
            circuit.execute(lambda: "probe 1")
            assert circuit.state == CircuitState.HALF_OPEN

            with pytest.raises(ValueError):
                circuit.execute(failing_func)
            assert circuit.state == CircuitState.OPEN

    def test_sliding_window_expires_old_failures(self):
        """Old failures outside the sliding window are not counted."""
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=10.0,
            failure_threshold=2,
            cooldown_seconds=5.0,
        )

        base_time = time.monotonic()

        def failing_func():
            raise ValueError("Simulated failure")

        with mock.patch("time.monotonic", return_value=base_time):
            with pytest.raises(ValueError):
                circuit.execute(failing_func)
            assert circuit.state == CircuitState.CLOSED

        with mock.patch("time.monotonic", return_value=base_time + 15.0):
            with pytest.raises(ValueError):
                circuit.execute(failing_func)
            assert circuit.state == CircuitState.CLOSED

        with mock.patch("time.monotonic", return_value=base_time + 15.1):
            with pytest.raises(ValueError):
                circuit.execute(failing_func)
            assert circuit.state == CircuitState.OPEN

    def test_circuit_breaker_as_decorator(self):
        """Circuit breaker can be used as a decorator."""
        circuit = CircuitBreaker(
            name="test_decorator",
            window_size_seconds=60.0,
            failure_threshold=2,
            cooldown_seconds=5.0,
        )

        call_count = 0

        @circuit
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError(f"Failure {call_count}")
            return f"Success at {call_count}"

        with pytest.raises(ValueError):
            sometimes_fails()
        with pytest.raises(ValueError):
            sometimes_fails()

        assert circuit.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerError):
            sometimes_fails()

    def test_reset_restores_initial_state(self):
        """Reset returns circuit to initial CLOSED state."""
        circuit = CircuitBreaker(
            name="test",
            window_size_seconds=60.0,
            failure_threshold=1,
            cooldown_seconds=5.0,
        )

        def failing_func():
            raise ValueError("Simulated failure")

        with pytest.raises(ValueError):
            circuit.execute(failing_func)

        assert circuit.state == CircuitState.OPEN
        assert circuit.metrics.failed_requests == 1

        circuit.reset()

        assert circuit.state == CircuitState.CLOSED
        assert circuit.metrics.failed_requests == 0
