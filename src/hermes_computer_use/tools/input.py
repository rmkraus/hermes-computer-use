"""Input simulation — keyboard and mouse input automation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

try:
    import pyautogui
except Exception:
    # Catches ImportError AND Xlib.error.DisplayNameError (raised by mouseinfo
    # at import time when DISPLAY is absent or invalid in headless environments)
    pyautogui = None  # type: ignore[assignment]
logger = logging.getLogger(__name__)


class MouseButton(StrEnum):
    """Mouse button identifiers."""

    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"


class KeyboardAction(StrEnum):
    """Keyboard action types."""

    PRESS = "press"
    RELEASE = "release"
    PRESS_RELEASE = "press_release"  # Press and release in one call
    TYPE = "type"  # Type text with press + release for each key


@dataclass
class ClickAction:
    """Mouse click action."""

    x: int
    y: int
    button: MouseButton = MouseButton.LEFT
    clicks: int = 1
    interval: float = 0.1


@dataclass
class MoveAction:
    """Mouse movement action."""

    x: int
    y: int
    duration: float = 0.5


@dataclass
class ScrollAction:
    """Mouse scroll action."""

    x: int
    y: int
    clicks: int  # Positive = up, Negative = down
    button: MouseButton = MouseButton.LEFT


@dataclass
class TypeAction:
    """Keyboard typing action."""

    text: str
    interval: float = 0.05
    log_keys: bool = True


@dataclass
class KeyComboAction:
    """Keyboard combination action (e.g., Ctrl+C)."""

    keys: list[str]  # e.g., ["ctrl", "shift", "c"]
    action: KeyboardAction = KeyboardAction.PRESS_RELEASE
    interval: float = 0.05


class InputSimulator:
    """Cross-platform input simulation engine.

    Uses PyAutoGUI as the primary backend with platform-specific fallbacks.
    Supports mouse movement, clicking, scrolling, keyboard typing, and
    key combinations.
    """

    def __init__(
        self,
        mouse_move_duration: float = 0.5,
        pause: float = 0.1,
        pag: Any | None = None,
    ) -> None:
        """Initialize the input simulator.

        Args:
            mouse_move_duration: Default duration for mouse movement in seconds.
            pause: Default pause between consecutive actions.
            pag: Optional pyautogui mock for testing.
        """
        self.mouse_move_duration = mouse_move_duration
        self.pause = pause
        self.pag = pag or pyautogui
        if self.pag is None:
            raise RuntimeError(
                "pyautogui is not installed. "
                "Install it with: pip install pyautogui"
            )
        self.pag.FAILSAFE = True
        self.pag.PAUSE = pause
        self._screen_width, self._screen_height = self._get_screen_size()

    def _get_screen_size(self) -> tuple[int, int]:
        """Get screen dimensions."""
        try:
            return self.pag.size()
        except Exception:
            return (1920, 1080)  # Fallback

    def click(
        self,
        x: int,
        y: int,
        button: MouseButton = MouseButton.LEFT,
        clicks: int = 1,
    ) -> dict[str, Any]:
        """Click at screen coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
            button: Which mouse button to click.
            clicks: Number of clicks (1=click, 2=double-click).

        Returns:
            Result dict with status and details.
        """
        pag = self.pag
        btn = button.value
        if clicks == 2:
            pag.doubleClick(x, y, button=btn)
        elif clicks == 3:
            pag.tripleClick(x, y, button=btn)
        else:
            pag.click(x, y, button=btn)

        return {
            "action": "click",
            "x": x,
            "y": y,
            "button": button.value,
            "clicks": clicks,
            "status": "success",
        }

    def move(self, x: int, y: int, duration: float | None = None) -> dict[str, Any]:
        """Move mouse to coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            duration: Animation duration in seconds.

        Returns:
            Result dict with status and details.
        """
        dur = duration if duration is not None else self.mouse_move_duration
        self.pag.moveTo(x, y, duration=dur)

        return {
            "action": "move",
            "x": x,
            "y": y,
            "duration": dur,
            "status": "success",
        }

    def scroll(self, x: int, y: int, clicks: int) -> dict[str, Any]:
        """Scroll mouse wheel at position.

        Args:
            x: X coordinate to scroll at.
            y: Y coordinate to scroll at.
            clicks: Number of scroll clicks (positive=up, negative=down).

        Returns:
            Result dict with status and details.
        """
        # PyAutoGUI scroll doesn't take x,y on Linux; it scrolls globally
        self.pag.scroll(clicks, x=x, y=y)

        return {
            "action": "scroll",
            "x": x,
            "y": y,
            "clicks": clicks,
            "status": "success",
        }

    def type_text(self, text: str, interval: float = 0.05) -> dict[str, Any]:
        """Type text character by character.

        Args:
            text: Text string to type.
            interval: Delay between keystrokes in seconds.

        Returns:
            Result dict with status and details.
        """
        self.pag.write(text, interval=interval)

        return {
            "action": "type",
            "text": text,
            "character_count": len(text),
            "status": "success",
        }

    def key_combo(
        self,
        keys: list[str],
        action: KeyboardAction = KeyboardAction.PRESS_RELEASE,
    ) -> dict[str, Any]:
        """Execute a key combination.

        Args:
            keys: List of key names (e.g., ["ctrl", "shift", "c"]).
            action: Whether to press, release, or press+release.

        Returns:
            Result dict with status and details.
        """
        pag = self.pag

        if action == KeyboardAction.PRESS_RELEASE:
            pag.hotkey(*keys)
        elif action == KeyboardAction.PRESS:
            for key in keys:
                pag.keyDown(key)
        elif action == KeyboardAction.RELEASE:
            for key in reversed(keys):
                pag.keyUp(key)

        return {
            "action": "key_combo",
            "keys": keys,
            "type": action.value,
            "status": "success",
        }

    def press_key(self, key: str) -> dict[str, Any]:
        """Press and release a single key.

        Args:
            key: Key name (e.g., "enter", "escape", "tab").

        Returns:
            Result dict with status and details.
        """
        self.pag.press(key)

        return {
            "action": "press_key",
            "key": key,
            "status": "success",
        }

    def screenshot_and_click(
        self,
        screenshot_path: str,
        target_image: str,
        confidence: float = 0.8,
    ) -> dict[str, Any]:
        """Take a screenshot and click on a visual target.

        Args:
            screenshot_path: Path to save screenshot for debugging.
            target_image: Path to image template to find.
            confidence: Minimum confidence for match.

        Returns:
            Result dict with click coordinates.
        """
        pag = self.pag

        try:
            location = pag.locateOnScreen(target_image, confidence=confidence)
            if location is None:
                return {
                    "action": "locate_and_click",
                    "status": "not_found",
                    "message": "Target image not found on screen",
                }

            center = pag.center(location)
            pag.click(center)

            return {
                "action": "locate_and_click",
                "x": center[0],
                "y": center[1],
                "confidence": confidence,
                "status": "success",
            }
        except Exception as e:
            return {
                "action": "locate_and_click",
                "status": "error",
                "message": str(e),
            }

    def wait(self, seconds: float) -> dict[str, Any]:
        """Pause for specified duration.

        Args:
            seconds: Number of seconds to wait.

        Returns:
            Result dict with status and details.
        """
        time.sleep(seconds)

        return {
            "action": "wait",
            "duration": seconds,
            "status": "success",
        }

    def reset_failsafe(self, enable: bool = True) -> dict[str, Any]:
        """Toggle PyAutoGUI failsafe (move mouse to corner to abort).

        Args:
            enable: Whether to enable the failsafe.

        Returns:
            Result dict with status.
        """
        self.pag.FAILSAFE = enable

        return {
            "action": "reset_failSafe",
            "enabled": enable,
            "status": "success",
        }
