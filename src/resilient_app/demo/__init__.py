"""Demo scenarios for resilient-app.

Demonstrates:
1. Normal successful execution
2. Circuit breaker open/rejection
3. Fallback success (primary fails, secondary succeeds)
4. Fallback failure (both paths fail)
"""

from resilient_app.demo.scenarios import (
    DemoResult,
    demo_circuit_open,
    demo_fallback_failure,
    demo_fallback_success,
    demo_normal,
    run_all_demos,
)

__all__ = [
    "DemoResult",
    "demo_normal",
    "demo_circuit_open",
    "demo_fallback_success",
    "demo_fallback_failure",
    "run_all_demos",
]
