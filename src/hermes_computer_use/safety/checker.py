"""Action safety checker — validates actions before execution."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SafetyCheckResult:
    """Result of a safety validation check."""

    safe: bool
    action: str
    reason: str | None = None
    warning: str | None = None
    blocked: bool = False
    requires_approval: bool = False


class SafetyChecker:
    """Validates actions for safety before execution.

    Implements multiple layers of safety checks:
    1. Text content analysis (dangerous commands, passwords)
    2. Key combination validation (system-critical shortcuts)
    3. Coordinate validation (screen boundary checks)
    4. Rate limiting (action frequency checks)
    """

    # Dangerous shell commands to block
    DANGEROUS_COMMANDS = [
        "rm -rf",
        "rm -r",
        "rm --no-preserve-root",
        "mkfs",
        "dd if=",
        ":(){ :|: & };:",  # Fork bomb
        "sudo shutdown",
        "sudo reboot",
        "sudo halt",
        "sudo poweroff",
        "chmod 777",
        "DROP TABLE",
        "DROP DATABASE",
        "TRUNCATE TABLE",
        "> /dev/sda",
        "format /dev",
        "apt-get purge",
        "pacman -Syu --noconfirm",
        "apt-get remove",
    ]

    # Critical system key combinations to block
    BLOCKED_KEY_COMBOS = [
        ["alt", "f4"],          # Close window
        ["ctrl", "alt", "delete"],  # System switch
        ["ctrl", "alt", "esc"],      # X kill
        ["ctrl", "alt", "backspace"], # X kill (old)
        ["super", "escape"],         # System menu
    ]

    def __init__(
        self,
        max_action_rate: float = 120.0,  # Actions per minute
        max_action_length: int = 5000,
    ) -> None:
        """Initialize safety checker.

        Args:
            max_action_rate: Maximum actions per minute.
            max_action_length: Maximum text length for typed input.
        """
        self.max_action_rate = max_action_rate
        self.max_action_length = max_action_length
        self._action_timestamps: list[float] = []

    def check_text(self, text: str) -> SafetyCheckResult:
        """Check text content for dangerous patterns.

        Args:
            text: Text to validate.

        Returns:
            SafetyCheckResult with safe/blocked status.
        """
        if len(text) > self.max_action_length:
            return SafetyCheckResult(
                safe=False,
                action="type",
                reason=f"Text exceeds max length {self.max_action_length}",
                blocked=True,
            )

        text_lower = text.lower().strip()

        # Check for dangerous commands
        for pattern in self.DANGEROUS_COMMANDS:
            if pattern.lower() in text_lower:
                return SafetyCheckResult(
                    safe=False,
                    action="type",
                    reason=f"Dangerous pattern detected: {pattern}",
                    blocked=True,
                )

        # Check for password-like content
        password_indicators = [
            "password:",
            "passwd:",
            "secret:",
            "api_key=",
            "token=",
            "apikey=",
            "access_key=",
            "secret_access_key=",
        ]

        for indicator in password_indicators:
            if indicator in text_lower:
                return SafetyCheckResult(
                    safe=False,
                    action="type",
                    reason="Possible password or secret detected",
                    blocked=True,
                    requires_approval=True,
                )

        return SafetyCheckResult(
            safe=True,
            action="type",
        )

    def check_key_combo(self, keys: list[str]) -> SafetyCheckResult:
        """Check if a key combination is safe to execute.

        Args:
            keys: List of keys in the combination.

        Returns:
            SafetyCheckResult with safe/blocked status.
        """
        for blocked_combo in self.BLOCKED_KEY_COMBOS:
            if sorted(keys) == sorted(blocked_combo):
                return SafetyCheckResult(
                    safe=False,
                    action="key_combo",
                    reason=f"System-critical key combination blocked: {'+'.join(keys)}",
                    blocked=True,
                )

        # Check for dangerous combinations
        if "ctrl" in keys and "alt" in keys and "delete" in keys:
            return SafetyCheckResult(
                safe=False,
                action="key_combo",
                reason="Potentially dangerous key combination detected",
                blocked=True,
            )

        return SafetyCheckResult(
            safe=True,
            action="key_combo",
        )

    def check_coordinate(self, x: int, y: int, screen_width: int, screen_height: int) -> SafetyCheckResult:
        """Check if screen coordinates are valid.

        Args:
            x: X coordinate.
            y: Y coordinate.
            screen_width: Screen width in pixels.
            screen_height: Screen height in pixels.

        Returns:
            SafetyCheckResult with safe/invalid status.
        """
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            return SafetyCheckResult(
                safe=False,
                action="click",
                reason=f"Coordinate ({x}, {y}) is outside screen bounds (0,0-{screen_width}x{screen_height})",
                blocked=True,
            )

        # Check if clicking on screen edges (possibly system UI)
        edge_threshold = 10
        on_edge = (
            x <= edge_threshold
            or y <= edge_threshold
            or x >= screen_width - edge_threshold
            or y >= screen_height - edge_threshold
        )

        if on_edge:
            return SafetyCheckResult(
                safe=True,
                action="click",
                warning="Coordinate near screen edge (system UI area)",
            )

        return SafetyCheckResult(
            safe=True,
            action="click",
        )

    def check_rate_limit(self) -> SafetyCheckResult:
        """Check if the action rate is within limits.

        Returns:
            SafetyCheckResult with safe/limited status.
        """
        now = time.time()

        # Count actions in the last minute
        recent_actions = [t for t in self._action_timestamps if t > now - 60]

        if len(recent_actions) >= self.max_action_rate:
            return SafetyCheckResult(
                safe=False,
                action="rate_limit",
                reason=f"Action rate limit exceeded: {len(recent_actions)}/{self.max_action_rate} per minute",
                blocked=True,
            )

        return SafetyCheckResult(
            safe=True,
            action="rate_limit",
        )

    def record_action(self) -> None:
        """Record an action for rate limiting."""
        self._action_timestamps.append(time.time())

        # Clean up old timestamps (older than 5 minutes)
        cutoff = time.time() - 300
        self._action_timestamps = [
            t for t in self._action_timestamps if t > cutoff
        ]

    def check_all(self, action_type: str, **kwargs: Any) -> SafetyCheckResult:
        """Run all applicable safety checks for an action.

        Args:
            action_type: Type of action being checked.
            **kwargs: Action parameters.

        Returns:
            SafetyCheckResult with combined status.
        """
        # Always check rate limit
        rate_result = self.check_rate_limit()
        if not rate_result.safe:
            return rate_result

        # Check based on action type
        if action_type in ("type", "key_combo"):
            text = kwargs.get("text", "")
            if text:
                text_result = self.check_text(text)
                if not text_result.safe:
                    return text_result

        if action_type == "key_combo":
            keys = kwargs.get("keys", [])
            if keys:
                combo_result = self.check_key_combo(keys)
                if not combo_result.safe:
                    return combo_result

        if action_type in ("click", "move"):
            x = kwargs.get("x", 0)
            y = kwargs.get("y", 0)
            screen_width = kwargs.get("screen_width", 1920)
            screen_height = kwargs.get("screen_height", 1080)
            coord_result = self.check_coordinate(x, y, screen_width, screen_height)
            if not coord_result.safe:
                return coord_result

        return SafetyCheckResult(safe=True, action=action_type)
