"""Tests for CLI module.

Covers:
- Argument parsing
- Exit codes
- stderr output with grep-able error codes
"""

import io
import sys
from unittest import mock

import pytest

from resilient_app.cli.main import ERROR_CODE_PREFIX, format_demo_result, get_exit_code, main
from resilient_app.core import CLI_ARGUMENT_ERROR, SUCCESS
from resilient_app.demo import DemoResult


class TestGetExitCode:
    """Test exit code mapping."""

    def test_success_returns_0(self):
        """SUCCESS code returns exit code 0."""
        assert get_exit_code(SUCCESS) == 0

    def test_argument_error_returns_2(self):
        """CLI_ARGUMENT_ERROR returns exit code 2."""
        assert get_exit_code(CLI_ARGUMENT_ERROR) == 2

    def test_other_error_returns_1(self):
        """Any other error code returns exit code 1."""
        assert get_exit_code("SOME_OTHER_ERROR") == 1


class TestFormatDemoResult:
    """Test demo result formatting."""

    def test_success_format(self):
        """Success result shows PASS indicator."""
        result = DemoResult(
            name="Test Scenario",
            operation_success=True,
            expected_code=SUCCESS,
            actual_code=SUCCESS,
            message="Test completed",
        )

        formatted = format_demo_result(result)

        assert "✓ PASS" in formatted
        assert "Test Scenario" in formatted
        assert "code matches expected" in formatted
        assert "operation succeeded" in formatted

    def test_failure_format(self):
        """Failure result shows FAIL indicator."""
        result = DemoResult(
            name="Test Scenario",
            operation_success=False,
            expected_code="EXPECTED",
            actual_code="ACTUAL",
            message="Test failed",
        )

        formatted = format_demo_result(result)

        assert "✗ FAIL" in formatted
        assert "code mismatch" in formatted
        assert "EXPECTED" in formatted
        assert "ACTUAL" in formatted

    def test_expected_failure_passes(self):
        """When code matches, scenario passes even if operation failed."""
        result = DemoResult(
            name="Expected Failure Scenario",
            operation_success=False,
            expected_code="CIRCUIT_OPEN",
            actual_code="CIRCUIT_OPEN",
            message="Circuit opened as expected",
        )

        formatted = format_demo_result(result)

        assert "✓ PASS" in formatted
        assert "operation failed - as expected" in formatted
        assert "code matches expected" in formatted


class TestMain:
    """Test CLI main function."""

    def test_main_without_args_shows_help(self):
        """Without arguments, main shows help and returns 0."""
        with mock.patch("sys.argv", ["resilient"]):
            exit_code = main()

        assert exit_code == 0

    def test_main_with_help_flag(self):
        """With --help flag, main returns 0."""
        with mock.patch("sys.argv", ["resilient", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
