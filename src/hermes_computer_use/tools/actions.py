"""High-level action primitives — composable actions for desktop automation."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .input import InputSimulator, KeyboardAction

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result of executing an action."""

    action: str
    success: bool
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration: float = 0.0


class ActionExecutor(Protocol):
    """Protocol for action executors."""

    def execute(self, action: str, **kwargs: Any) -> ActionResult: ...


class DesktopActionExecutor:
    """High-level action executor that composes lower-level primitives.

    Provides user-friendly action names that map to complex sequences
    of low-level operations.
    """

    def __init__(self, input_simulator: InputSimulator | None = None) -> None:
        """Initialize the action executor.

        Args:
            input_simulator: Input simulator instance. Created if None.
        """
        self.input_simulator = input_simulator or InputSimulator()

    def execute(self, action: str, **kwargs: Any) -> ActionResult:
        """Execute a high-level action.

        Args:
            action: Action name (e.g., 'click', 'type', 'open_app', 'navigate').
            **kwargs: Action-specific parameters.

        Returns:
            ActionResult with success/failure status.
        """
        start_time = time.time()

        try:
            handler = getattr(self, f"_execute_{action}", None)
            if handler is None:
                return ActionResult(
                    action=action,
                    success=False,
                    error=f"Unknown action: {action}",
                )

            result = handler(**kwargs)
            return ActionResult(
                action=action,
                success=True,
                result=result,
                duration=time.time() - start_time,
            )

        except Exception as e:
            return ActionResult(
                action=action,
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )

    def _execute_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        """Click at screen coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
            button: Mouse button (left/middle/right).
            clicks: Number of clicks.
        """
        from .input import MouseButton

        return self.input_simulator.click(
            x, y,
            button=MouseButton(button),
            clicks=clicks,
        )

    def _execute_type(self, text: str, delay: float = 0.05) -> dict[str, Any]:
        """Type text.

        Args:
            text: Text to type.
            delay: Delay between keystrokes.
        """
        return self.input_simulator.type_text(text, interval=delay)

    def _execute_key(self, key: str, combo: list[str] | None = None) -> dict[str, Any]:
        """Press a key or key combination.

        Args:
            key: Key to press.
            combo: Optional list of modifier keys.
        """
        if combo:
            keys = combo + [key]
            return self.input_simulator.key_combo(keys)
        return self.input_simulator.press_key(key)

    def _execute_open_app(self, app_name: str, args: list[str] | None = None) -> dict[str, Any]:
        """Open an application.

        Args:
            app_name: Application name or command.
            args: Additional command arguments.
        """
        try:
            cmd = [app_name] + (args or [])
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return {
                "action": "open_app",
                "app": app_name,
                "args": args,
                "status": "launched",
            }
        except Exception as e:
            return {
                "action": "open_app",
                "app": app_name,
                "status": "error",
                "error": str(e),
            }

    def _execute_navigate(self, url: str) -> dict[str, Any]:
        """Open a URL in the default browser.

        Args:
            url: URL to open.
        """
        try:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return {
                "action": "navigate",
                "url": url,
                "status": "opened",
            }
        except Exception as e:
            return {
                "action": "navigate",
                "url": url,
                "status": "error",
                "error": str(e),
            }

    def _execute_wait(self, seconds: float = 1.0) -> dict[str, Any]:
        """Wait for specified duration.

        Args:
            seconds: Seconds to wait.
        """
        time.sleep(seconds)
        return {"action": "wait", "duration": seconds, "status": "completed"}

    def _execute_search(self, text: str, delay: float = 0.1) -> dict[str, Any]:
        """Open application search and type text.

        Args:
            text: Application name to search for.
            delay: Delay between keystrokes.
        """
        try:
            # Press Super key to open application launcher
            self.input_simulator.press_key("super")
            time.sleep(0.5)

            # Type search text
            self.input_simulator.type_text(text, interval=delay)

            return {
                "action": "search",
                "query": text,
                "status": "searching",
            }
        except Exception as e:
            return {
                "action": "search",
                "query": text,
                "status": "error",
                "error": str(e),
            }

    def _execute_screenshot(self, path: str | None = None) -> dict[str, Any]:
        """Take a screenshot.

        Args:
            path: Optional path to save screenshot.
        """
        from .screenshot import capture_screenshot

        try:
            screenshot = capture_screenshot()

            if path:
                with open(path, "wb") as f:
                    f.write(screenshot.data)

            return {
                "action": "screenshot",
                "width": screenshot.width,
                "height": screenshot.height,
                "status": "captured",
                "format": "png",
            }
        except Exception as e:
            return {
                "action": "screenshot",
                "status": "error",
                "error": str(e),
            }

    def execute_sequence(self, actions: list[dict[str, Any]]) -> list[ActionResult]:
        """Execute a sequence of actions.

        Args:
            actions: List of action dicts with 'action' and 'params' keys.

        Returns:
            List of results for each action.
        """
        results = []
        for action_spec in actions:
            action_name = action_spec.get("action", "")
            params = action_spec.get("params", {})
            result = self.execute(action_name, **params)
            results.append(result)

            if not result.success:
                logger.warning("Action sequence failed at step %s: %s", action_name, result.error)
                break

        return results
