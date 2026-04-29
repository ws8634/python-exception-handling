"""Command-line interface entry point.

This layer:
- Parses arguments
- Calls application layer
- Sets exit codes
- Outputs user-friendly messages to stderr
- Does NOT print raw tracebacks to users
- Ensures error codes are grep-able

Exit codes:
- 0: Success
- 1: General error
- 2: Argument error
- Custom: Based on error category
"""

import argparse
import sys
from typing import Sequence

from resilient_app.core import (
    CLI_ARGUMENT_ERROR,
    CLI_EXECUTION_ERROR,
    SUCCESS,
    setup_logging,
)
from resilient_app.demo import DemoResult, run_all_demos

ERROR_CODE_PREFIX = "ERROR_CODE:"


def print_error_message(message: str, code: str) -> None:
    """Print a user-friendly error message to stderr.

    Includes error code in a grep-able format.

    Args:
        message: Human-readable message.
        code: Error code for grepping.
    """
    print(f"Error: {message}", file=sys.stderr)
    print(f"{ERROR_CODE_PREFIX}{code}", file=sys.stderr)


def print_success_message(message: str) -> None:
    """Print a success message to stdout.

    Args:
        message: Human-readable message.
    """
    print(f"Success: {message}", file=sys.stdout)


def format_demo_result(result: DemoResult) -> str:
    """Format a demo result for display.

    Args:
        result: DemoResult to format.

    Returns:
        Formatted string for output.
    """
    scenario_passed = result.passed
    status = "✓ PASS" if scenario_passed else "✗ FAIL"
    op_status = " (operation succeeded)" if result.operation_success else " (operation failed - as expected)"
    code_match = (
        " (code matches expected)"
        if result.actual_code == result.expected_code
        else f" (code mismatch: expected={result.expected_code}, actual={result.actual_code})"
    )
    return f"[{status}] {result.name}: {result.message}{op_status}{code_match}"


def get_exit_code(code: str) -> int:
    """Map error code to exit code.

    Args:
        code: Error code string.

    Returns:
        Integer exit code (0 for success, >0 for errors).
    """
    if code == SUCCESS:
        return 0

    if code == CLI_ARGUMENT_ERROR:
        return 2

    return 1


def run_demo() -> int:
    """Run all demo scenarios.

    Returns:
        Exit code (0 if all demos ran, 1 if any demo failed unexpectedly).
    """
    print("=" * 60, file=sys.stderr)
    print("Running resilience patterns demo...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    results = run_all_demos()

    print("\n" + "=" * 60, file=sys.stderr)
    print("Demo Results Summary:", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    all_passed = True
    for result in results:
        formatted = format_demo_result(result)
        if result.passed:
            print(formatted, file=sys.stdout)
        else:
            print(formatted, file=sys.stderr)
        if not result.passed:
            all_passed = False

    if all_passed:
        print("\nAll demos completed as expected!", file=sys.stdout)
        print(f"{ERROR_CODE_PREFIX}{SUCCESS}", file=sys.stderr)
        return 0
    else:
        print("\nSome demos did not behave as expected.", file=sys.stderr)
        print(f"{ERROR_CODE_PREFIX}{CLI_EXECUTION_ERROR}", file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="resilient",
        description="Resilient application with engineering-grade exception handling",
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration of all resilience patterns",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG level logging",
    )

    args = parser.parse_args(argv)

    setup_logging(debug=args.debug)

    if args.demo:
        return run_demo()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
