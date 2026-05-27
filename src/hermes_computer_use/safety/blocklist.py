"""Action blocklist — predefined list of blocked actions and patterns."""

from __future__ import annotations

import re
from typing import Any


# Blocklist of action patterns that are never allowed
ACTION_BLOCKLIST: list[dict[str, Any]] = [
    {
        "action": "type",
        "pattern": r"(?i)(rm\s+-rf|mkfs|dd\s+if=|sudo\s+shutdown|sudo\s+reboot)",
        "reason": "Dangerous shell command",
    },
    {
        "action": "type",
        "pattern": r"(?i)(password|secret|token|api[_-]?key)\s*[:=]",
        "reason": "Possible credential input",
    },
    {
        "action": "key_combo",
        "keys": ["ctrl", "alt", "delete"],
        "reason": "System-critical key combination",
    },
    {
        "action": "key_combo",
        "keys": ["ctrl", "alt", "esc"],
        "reason": "X server kill combination",
    },
    {
        "action": "click",
        "coordinate": {"x": 0, "y": 0},
        "reason": "System corner (may trigger system UI)",
    },
]

# Global blocklist status
_BLOCKLIST_ENABLED = True


def is_action_blocked(action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check if an action is in the blocklist.

    Args:
        action: Action name to check.
        params: Action parameters.

    Returns:
        Dict with 'blocked' (bool) and 'reason' (str if blocked).
    """
    if not _BLOCKLIST_ENABLED:
        return {"blocked": False, "reason": None}

    params = params or {}

    for rule in ACTION_BLOCKLIST:
        if rule["action"] != action:
            continue

        # Check pattern match
        if "pattern" in rule:
            for value in params.values():
                if isinstance(value, str) and re.search(rule["pattern"], value):
                    return {"blocked": True, "reason": rule["reason"]}

        # Check specific values
        if "keys" in rule:
            if params.get("keys") == rule["keys"]:
                return {"blocked": True, "reason": rule["reason"]}

        if "coordinate" in rule:
            if params.get("x") == rule["coordinate"]["x"] and params.get("y") == rule["coordinate"]["y"]:
                return {"blocked": True, "reason": rule["reason"]}

    return {"blocked": False, "reason": None}


def enable_blocklist() -> None:
    """Enable the action blocklist."""
    global _BLOCKLIST_ENABLED
    _BLOCKLIST_ENABLED = True


def disable_blocklist() -> None:
    """Disable the action blocklist."""
    global _BLOCKLIST_ENABLED
    _BLOCKLIST_ENABLED = False


def get_blocked_actions() -> list[dict[str, Any]]:
    """Get the current blocklist."""
    return ACTION_BLOCKLIST.copy()


def add_blocked_action(action: str, pattern: str | None = None, reason: str = "Custom block") -> None:
    """Add a custom blocked action pattern.

    Args:
        action: Action name.
        pattern: Regex pattern to match.
        reason: Reason for blocking.
    """
    rule: dict[str, Any] = {"action": action, "reason": reason}
    if pattern:
        rule["pattern"] = pattern

    ACTION_BLOCKLIST.append(rule)


def remove_blocked_action(action: str, reason: str | None = None) -> None:
    """Remove a blocked action pattern.

    Args:
        action: Action name.
        reason: Optional reason to match.
    """
    for i, rule in enumerate(ACTION_BLOCKLIST):
        if rule["action"] == action and (reason is None or rule.get("reason") == reason):
            ACTION_BLOCKLIST.pop(i)
            return
