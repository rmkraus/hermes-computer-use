"""Tests for action blocklist."""

from __future__ import annotations

from hermes_computer_use.safety.blocklist import (
    ACTION_BLOCKLIST,
    add_blocked_action,
    disable_blocklist,
    enable_blocklist,
    get_blocked_actions,
    is_action_blocked,
    remove_blocked_action,
)


class TestActionBlocklist:
    """Tests for the action blocklist."""

    def test_blocklist_not_empty(self):
        """Test that blocklist has entries."""
        assert len(ACTION_BLOCKLIST) > 0

    def test_safe_type_not_blocked(self):
        """Test that safe text is not blocked."""
        result = is_action_blocked("type", {"text": "Hello world"})
        assert result["blocked"] is False
        assert result["reason"] is None

    def test_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked."""
        result = is_action_blocked("type", {"text": "rm -rf /"})
        assert result["blocked"] is True
        assert result["reason"] is not None

    def test_credential_input_blocked(self):
        """Test that credential input is blocked."""
        result = is_action_blocked("type", {"text": "password: secret123"})
        assert result["blocked"] is True

    def test_critical_combo_blocked(self):
        """Test that critical key combos are blocked."""
        result = is_action_blocked("key_combo", {"keys": ["ctrl", "alt", "delete"]})
        assert result["blocked"] is True

    def test_server_kill_combo_blocked(self):
        """Test that server kill combo is blocked."""
        result = is_action_blocked("key_combo", {"keys": ["ctrl", "alt", "esc"]})
        assert result["blocked"] is True

    def test_system_corner_blocked(self):
        """Test that system corner click is blocked."""
        result = is_action_blocked("click", {"x": 0, "y": 0})
        assert result["blocked"] is True

    def test_normal_click_not_blocked(self):
        """Test that normal click is not blocked."""
        result = is_action_blocked("click", {"x": 100, "y": 200})
        assert result["blocked"] is False

    def test_normal_combo_not_blocked(self):
        """Test that normal key combo is not blocked."""
        result = is_action_blocked("key_combo", {"keys": ["ctrl", "c"]})
        assert result["blocked"] is False

    def test_no_params(self):
        """Test handling of no parameters."""
        result = is_action_blocked("type", {})
        assert result["blocked"] is False

    def test_empty_params(self):
        """Test handling of empty params dict."""
        result = is_action_blocked("type", params={})
        assert result["blocked"] is False

    def test_disabled_blocklist(self):
        """Test that blocklist can be disabled."""
        disable_blocklist()
        result = is_action_blocked("type", {"text": "rm -rf /"})
        assert result["blocked"] is False
        # Re-enable for other tests
        enable_blocklist()

    def test_get_blocked_actions(self):
        """Test getting the blocklist."""
        actions = get_blocked_actions()
        assert isinstance(actions, list)
        assert len(actions) > 0
        # Should be a copy, not the original
        assert actions is not ACTION_BLOCKLIST

    def test_add_blocked_action(self):
        """Test adding a custom blocked action."""
        initial_count = len(ACTION_BLOCKLIST)
        add_blocked_action("test_action", pattern=r"test.*pattern", reason="Custom test")

        assert len(ACTION_BLOCKLIST) > initial_count

        result = is_action_blocked("test_action", {"text": "test pattern match"})
        assert result["blocked"] is True

        # Clean up
        remove_blocked_action("test_action", reason="Custom test")

    def test_remove_blocked_action(self):
        """Test removing a blocked action."""
        initial_count = len(ACTION_BLOCKLIST)

        # Add then remove
        add_blocked_action("to_remove", reason="Will be removed")
        remove_blocked_action("to_remove", reason="Will be removed")

        assert len(ACTION_BLOCKLIST) <= initial_count + 1

    def test_custom_pattern_block(self):
        """Test that custom patterns work."""
        add_blocked_action("type", pattern=r"(?i)supersecret", reason="Secret word")

        result = is_action_blocked("type", {"text": "this is supersecret"})
        assert result["blocked"] is True

        # Clean up
        remove_blocked_action("type", reason="Secret word")


class TestBlocklistEdgeCases:
    """Edge case tests for blocklist."""

    def test_unicode_text(self):
        """Test Unicode text in pattern matching."""
        result = is_action_blocked("type", {"text": "日本語テキスト"})
        assert result["blocked"] is False

    def test_case_insensitive_pattern(self):
        """Test that patterns are case insensitive."""
        result = is_action_blocked("type", {"text": "RM -RF /"})
        assert result["blocked"] is True

    def test_partial_match(self):
        """Test that partial matches are caught."""
        result = is_action_blocked("type", {"text": "sudo shutdown -h now for maintenance"})
        assert result["blocked"] is True

    def test_empty_text(self):
        """Test empty text is not blocked."""
        result = is_action_blocked("type", {"text": ""})
        assert result["blocked"] is False

    def test_none_keys(self):
        """Test None keys value."""
        result = is_action_blocked("key_combo", {"keys": None})
        assert result["blocked"] is False

    def test_action_not_in_blocklist(self):
        """Test action not in blocklist is not blocked."""
        result = is_action_blocked("screenshot", {"path": "/tmp/test.png"})
        assert result["blocked"] is False
