"""Action safety checker — validates actions before execution."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SafetyCheckResult:
    """Result of a safety validation check."""

    def __init__(
        self,
        safe: bool,
        action: str,
        reason: str | None = None,
        blocked: bool = False,
    ) -> None:
        self.safe = safe
        self.action = action
        self.reason = reason
        self.blocked = blocked

    def __repr__(self) -> str:
        return f"SafetyCheckResult(safe={self.safe}, action={self.action!r}, reason={self.reason!r})"


class SafetyChecker:
    """Validates actions for safety before execution.

    Three layers of checks:
    1. Text content — dangerous shell commands, credentials
    2. Key combinations — system-critical shortcuts
    3. Screen coordinates — out-of-bounds clicks
    """

    # Dangerous shell command substrings
    DANGEROUS_COMMANDS = [
        "rm -rf",
        "rm -r",
        "rm --no-preserve-root",
        "mkfs",
        "dd if=",
        ":(){ :|: & };:",   # fork bomb
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
        "apt-get remove",
    ]

    # Key combos that must never be sent
    BLOCKED_KEY_COMBOS = [
        ["alt", "f4"],
        ["ctrl", "alt", "delete"],
        ["ctrl", "alt", "esc"],
        ["ctrl", "alt", "backspace"],
        ["super", "escape"],
    ]

    def check_text(self, text: str, max_length: int = 5000) -> SafetyCheckResult:
        """Check text for dangerous commands or credential patterns."""
        if len(text) > max_length:
            return SafetyCheckResult(
                safe=False,
                action="type",
                reason=f"Text exceeds max length {max_length}",
                blocked=True,
            )

        text_lower = text.lower().strip()

        for pattern in self.DANGEROUS_COMMANDS:
            if pattern.lower() in text_lower:
                return SafetyCheckResult(
                    safe=False,
                    action="type",
                    reason=f"Dangerous pattern detected: {pattern}",
                    blocked=True,
                )

        credential_indicators = [
            "password:",
            "passwd:",
            "secret:",
            "api_key=",
            "token=",
            "apikey=",
            "access_key=",
            "secret_access_key=",
        ]
        for indicator in credential_indicators:
            if indicator in text_lower:
                return SafetyCheckResult(
                    safe=False,
                    action="type",
                    reason="Possible credential detected",
                    blocked=True,
                )

        return SafetyCheckResult(safe=True, action="type")

    def check_key_combo(self, keys: list[str]) -> SafetyCheckResult:
        """Check if a key combination is safe to execute."""
        for blocked in self.BLOCKED_KEY_COMBOS:
            if sorted(keys) == sorted(blocked):
                return SafetyCheckResult(
                    safe=False,
                    action="key_combo",
                    reason=f"System-critical key combination blocked: {'+'.join(keys)}",
                    blocked=True,
                )
        return SafetyCheckResult(safe=True, action="key_combo")

    def check_coordinate(
        self, x: int, y: int, screen_width: int, screen_height: int
    ) -> SafetyCheckResult:
        """Check that screen coordinates are within bounds."""
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            return SafetyCheckResult(
                safe=False,
                action="click",
                reason=f"Coordinate ({x}, {y}) out of bounds ({screen_width}x{screen_height})",
                blocked=True,
            )
        return SafetyCheckResult(safe=True, action="click")
