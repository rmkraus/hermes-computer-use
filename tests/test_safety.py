"""Tests for action safety checker."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from hermes_computer_use.safety.checker import SafetyCheckResult, SafetyChecker


class TestSafetyCheckerText:
    """Tests for text content safety checks."""

    def test_safe_text(self):
        """Test that normal text passes safety check."""
        checker = SafetyChecker()
        result = checker.check_text("Hello, world!")

        assert result.safe is True
        assert result.action == "type"
        assert result.reason is None

    def test_dangerous_rm_rf(self):
        """Test blocking of rm -rf command."""
        checker = SafetyChecker()
        result = checker.check_text("rm -rf /")

        assert result.safe is False
        assert result.blocked is True
        assert "Dangerous pattern" in result.reason

    def test_dangerous_mkfs(self):
        """Test blocking of mkfs command."""
        checker = SafetyChecker()
        result = checker.check_text("mkfs.ext4 /dev/sda")

        assert result.safe is False
        assert result.blocked is True

    def test_dangerous_fork_bomb(self):
        """Test blocking of fork bomb."""
        checker = SafetyChecker()
        result = checker.check_text(":(){ :|: & };:")

        assert result.safe is False
        assert result.blocked is True

    def test_dangerous_shutdown(self):
        """Test blocking of shutdown commands."""
        checker = SafetyChecker()
        result = checker.check_text("sudo shutdown -h now")

        assert result.safe is False
        assert result.blocked is True

    def test_dangerous_drop_table(self):
        """Test blocking of SQL injection."""
        checker = SafetyChecker()
        result = checker.check_text("DROP TABLE users;")

        assert result.safe is False
        assert result.blocked is True

    def test_password_detection(self):
        """Test detecting password-like content."""
        checker = SafetyChecker()
        result = checker.check_text("password: secret123")

        assert result.safe is False
        assert result.requires_approval is True
        assert "password" in result.reason.lower() or "secret" in result.reason.lower()

    def test_api_key_detection(self):
        """Test detecting API key content."""
        checker = SafetyChecker()
        result = checker.check_text("api_key=abc123def456")

        assert result.safe is False
        assert result.requires_approval is True

    def test_token_detection(self):
        """Test detecting token content."""
        checker = SafetyChecker()
        result = checker.check_text("token=xyz789")

        assert result.safe is False
        assert result.requires_approval is True

    def test_too_long_text(self):
        """Test blocking overly long text."""
        checker = SafetyChecker(max_action_length=100)
        result = checker.check_text("x" * 200)

        assert result.safe is False
        assert result.blocked is True
        assert "max length" in result.reason.lower()

    def test_short_text_passes(self):
        """Test that short text passes."""
        checker = SafetyChecker(max_action_length=100)
        result = checker.check_text("Short text")

        assert result.safe is True


class TestSafetyCheckerKeyCombo:
    """Tests for key combination safety checks."""

    def test_safe_key_combo(self):
        """Test that normal key combos pass."""
        checker = SafetyChecker()
        result = checker.check_key_combo(["ctrl", "c"])

        assert result.safe is True

    def test_safe_key_combo_shift(self):
        """Test that shift-based combos pass."""
        checker = SafetyChecker()
        result = checker.check_key_combo(["shift", "delete"])

        assert result.safe is True

    def test_blocked_ctrl_alt_del(self):
        """Test blocking Ctrl+Alt+Delete."""
        checker = SafetyChecker()
        result = checker.check_key_combo(["ctrl", "alt", "delete"])

        assert result.safe is False
        assert result.blocked is True
        assert "System-critical" in result.reason

    def test_blocked_ctrl_alt_esc(self):
        """Test blocking Ctrl+Alt+Esc."""
        checker = SafetyChecker()
        result = checker.check_key_combo(["ctrl", "alt", "esc"])

        assert result.safe is False
        assert result.blocked is True

    def test_blocked_ctrl_alt_backspace(self):
        """Test blocking Ctrl+Alt+Backspace."""
        checker = SafetyChecker()
        result = checker.check_key_combo(["ctrl", "alt", "backspace"])

        assert result.safe is False
        assert result.blocked is True

    def test_dangerous_combo(self):
        """Test blocking potentially dangerous combinations."""
        checker = SafetyChecker()
        result = checker.check_key_combo(["ctrl", "alt", "delete"])

        assert result.safe is False


class TestSafetyCheckerCoordinate:
    """Tests for coordinate safety checks."""

    def test_valid_coordinate(self):
        """Test valid coordinate passes."""
        checker = SafetyChecker()
        result = checker.check_coordinate(500, 300, 1920, 1080)

        assert result.safe is True

    def test_out_of_bounds_x(self):
        """Test blocking out-of-bounds X coordinate."""
        checker = SafetyChecker()
        result = checker.check_coordinate(2000, 500, 1920, 1080)

        assert result.safe is False
        assert result.blocked is True
        assert "outside screen bounds" in result.reason

    def test_out_of_bounds_y(self):
        """Test blocking out-of-bounds Y coordinate."""
        checker = SafetyChecker()
        result = checker.check_coordinate(500, 1200, 1920, 1080)

        assert result.safe is False
        assert result.blocked is True

    def test_negative_coordinate(self):
        """Test blocking negative coordinates."""
        checker = SafetyChecker()
        result = checker.check_coordinate(-10, 100, 1920, 1080)

        assert result.safe is False
        assert result.blocked is True

    def test_screen_edge_warning(self):
        """Test warning for edge coordinates."""
        checker = SafetyChecker()
        result = checker.check_coordinate(5, 5, 1920, 1080)

        assert result.safe is True  # Safe, but with warning
        assert result.warning is not None
        assert "screen edge" in result.warning.lower()

    def test_screen_edge_x_right(self):
        """Test edge coordinate on right side."""
        checker = SafetyChecker()
        result = checker.check_coordinate(1915, 500, 1920, 1080)

        assert result.safe is True
        assert result.warning is not None

    def test_screen_edge_y_bottom(self):
        """Test edge coordinate on bottom."""
        checker = SafetyChecker()
        result = checker.check_coordinate(500, 1075, 1920, 1080)

        assert result.safe is True
        assert result.warning is not None

    def test_center_coordinates(self):
        """Test center coordinates have no warning."""
        checker = SafetyChecker()
        result = checker.check_coordinate(960, 540, 1920, 1080)

        assert result.safe is True
        assert result.warning is None


class TestSafetyCheckerRateLimit:
    """Tests for rate limiting checks."""

    def test_under_rate_limit(self):
        """Test that being under rate limit is safe."""
        checker = SafetyChecker(max_action_rate=5)
        # No prior actions, should be safe
        result = checker.check_rate_limit()
        assert result.safe is True

    def test_over_rate_limit(self):
        """Test that exceeding rate limit is blocked."""
        checker = SafetyChecker(max_action_rate=5)

        # Simulate 5 actions
        for _ in range(5):
            checker.record_action()

        result = checker.check_rate_limit()
        assert result.safe is False
        assert result.blocked is True
        assert "rate limit" in result.reason.lower()

    def test_record_action(self):
        """Test that actions are recorded."""
        checker = SafetyChecker(max_action_rate=100)
        before = len(checker._action_timestamps)
        checker.record_action()
        after = len(checker._action_timestamps)
        assert after == before + 1

    def test_rate_limit_cleanup(self):
        """Test that old timestamps are cleaned up."""
        checker = SafetyChecker(max_action_rate=100)

        # Record some actions
        for _ in range(3):
            checker.record_action()

        assert len(checker._action_timestamps) == 3


class TestSafetyCheckerAll:
    """Tests for combined safety checks."""

    def test_safe_action(self, mock_input_simulator):
        """Test that safe actions pass all checks."""
        checker = SafetyChecker()
        result = checker.check_all(
            "click",
            x=500,
            y=300,
            screen_width=1920,
            screen_height=1080,
        )
        assert result.safe is True

    def test_unsafe_text_in_all(self):
        """Test that unsafe text is caught in check_all."""
        checker = SafetyChecker()
        result = checker.check_all(
            "type",
            text="rm -rf /",
        )
        assert result.safe is False
        assert result.blocked is True

    def test_unsafe_combo_in_all(self):
        """Test that unsafe key combo is caught in check_all."""
        checker = SafetyChecker()
        result = checker.check_all(
            "key_combo",
            keys=["ctrl", "alt", "delete"],
        )
        assert result.safe is False
        assert result.blocked is True

    def test_unsafe_coordinate_in_all(self):
        """Test that unsafe coordinate is caught in check_all."""
        checker = SafetyChecker()
        result = checker.check_all(
            "click",
            x=5000,
            y=500,
            screen_width=1920,
            screen_height=1080,
        )
        assert result.safe is False
        assert result.blocked is True

    def test_empty_action(self):
        """Test empty action passes."""
        checker = SafetyChecker()
        result = checker.check_all("empty")
        assert result.safe is True


class TestSafetyCheckResult:
    """Tests for SafetyCheckResult dataclass."""

    def test_safe_result(self):
        """Test creating a safe result."""
        result = SafetyCheckResult(safe=True, action="type")
        assert result.safe is True
        assert result.action == "type"
        assert result.blocked is False

    def test_blocked_result(self):
        """Test creating a blocked result."""
        result = SafetyCheckResult(
            safe=False,
            action="type",
            reason="Dangerous pattern",
            blocked=True,
        )
        assert result.safe is False
        assert result.blocked is True
        assert result.reason == "Dangerous pattern"

    def test_warning_result(self):
        """Test creating a warning result."""
        result = SafetyCheckResult(
            safe=True,
            action="click",
            warning="Near edge of screen",
        )
        assert result.safe is True
        assert result.warning == "Near edge of screen"
