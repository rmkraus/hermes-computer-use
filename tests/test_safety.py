"""Tests for action safety checker."""

from __future__ import annotations

from hermes_computer_use.safety.checker import SafetyChecker, SafetyCheckResult


class TestSafetyCheckerText:
    """Tests for text content safety checks."""

    def test_safe_text(self):
        result = SafetyChecker().check_text("Hello, world!")
        assert result.safe is True
        assert result.action == "type"
        assert result.reason is None

    def test_dangerous_rm_rf(self):
        result = SafetyChecker().check_text("rm -rf /")
        assert result.safe is False
        assert "Dangerous pattern" in result.reason

    def test_dangerous_mkfs(self):
        result = SafetyChecker().check_text("mkfs.ext4 /dev/sda")
        assert result.safe is False

    def test_dangerous_fork_bomb(self):
        result = SafetyChecker().check_text(":(){ :|: & };:")
        assert result.safe is False

    def test_dangerous_shutdown(self):
        result = SafetyChecker().check_text("sudo shutdown -h now")
        assert result.safe is False

    def test_dangerous_drop_table(self):
        result = SafetyChecker().check_text("DROP TABLE users;")
        assert result.safe is False

    def test_password_detection(self):
        result = SafetyChecker().check_text("password: secret123")
        assert result.safe is False
        assert "credential" in result.reason.lower()

    def test_api_key_detection(self):
        result = SafetyChecker().check_text("api_key=abc123def456")
        assert result.safe is False

    def test_token_detection(self):
        result = SafetyChecker().check_text("token=xyz789")
        assert result.safe is False

    def test_too_long_text(self):
        result = SafetyChecker().check_text("x" * 200, max_length=100)
        assert result.safe is False
        assert "max length" in result.reason.lower()

    def test_short_text_passes(self):
        result = SafetyChecker().check_text("Short text", max_length=100)
        assert result.safe is True


class TestSafetyCheckerKeyCombo:
    """Tests for key combination safety checks."""

    def test_safe_key_combo(self):
        result = SafetyChecker().check_key_combo(["ctrl", "c"])
        assert result.safe is True

    def test_safe_key_combo_shift(self):
        result = SafetyChecker().check_key_combo(["shift", "delete"])
        assert result.safe is True

    def test_blocked_ctrl_alt_del(self):
        result = SafetyChecker().check_key_combo(["ctrl", "alt", "delete"])
        assert result.safe is False
        assert "System-critical" in result.reason

    def test_blocked_ctrl_alt_esc(self):
        result = SafetyChecker().check_key_combo(["ctrl", "alt", "esc"])
        assert result.safe is False

    def test_blocked_ctrl_alt_backspace(self):
        result = SafetyChecker().check_key_combo(["ctrl", "alt", "backspace"])
        assert result.safe is False

    def test_blocked_alt_f4(self):
        result = SafetyChecker().check_key_combo(["alt", "f4"])
        assert result.safe is False

    def test_blocked_super_escape(self):
        result = SafetyChecker().check_key_combo(["super", "escape"])
        assert result.safe is False


class TestSafetyCheckResult:
    """Tests for SafetyCheckResult."""

    def test_safe_result(self):
        result = SafetyCheckResult(safe=True, action="type")
        assert result.safe is True
        assert result.action == "type"
        assert result.reason is None

    def test_unsafe_result(self):
        result = SafetyCheckResult(safe=False, action="type", reason="Dangerous pattern")
        assert result.safe is False
        assert result.reason == "Dangerous pattern"

    def test_repr(self):
        result = SafetyCheckResult(safe=True, action="click")
        assert "True" in repr(result)
        assert "click" in repr(result)
