"""NAT tool registrations for desktop automation.

Each function here is registered with NAT's @register_function decorator
and exposed as a callable tool the react_agent can invoke.

Tools:
  - take_screenshot        capture current screen as base64 PNG
  - mouse_move             move cursor to (x, y)
  - mouse_click            click at (x, y) with optional button
  - mouse_double_click     double-click at (x, y)
  - mouse_scroll           scroll at (x, y) by delta
  - keyboard_type          type a string of text
  - keyboard_key           press a single key (e.g. Return, Escape, Tab)
  - keyboard_hotkey        press a key combination (e.g. ctrl+c)
  - list_windows           list open windows with title/geometry
  - focus_window           focus a window by title substring
  - check_action_safety    validate an action against the safety blocklist
"""

from __future__ import annotations

import json
import logging

from pydantic import Field

from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from hermes_computer_use.safety.checker import SafetyChecker
from hermes_computer_use.tools.actions import DesktopActionExecutor
from hermes_computer_use.tools.screenshot import capture_screenshot
from hermes_computer_use.tools.window import WindowManager

logger = logging.getLogger(__name__)

_safety = SafetyChecker()


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------


class TakeScreenshotConfig(FunctionBaseConfig, name="take_screenshot"):
    """Configuration for take_screenshot tool."""

    display: str = Field(":0", description="X11 display to capture (default :0)")
    max_dimension: int = Field(1024, description="Resize longest edge to this many pixels")


@register_function(config_type=TakeScreenshotConfig)
async def take_screenshot_tool(config: TakeScreenshotConfig, builder):
    """Capture the current screen and return a base64-encoded PNG image."""

    async def _fn() -> str:
        """Take a screenshot of the current screen.

        Returns a JSON string with:
          - image_b64: base64-encoded PNG data
          - width: screen width in pixels
          - height: screen height in pixels
          - urn: data URI usable directly in vision model messages
        """
        import os

        os.environ.setdefault("DISPLAY", config.display)
        shot = capture_screenshot()
        if shot is None:
            return json.dumps({"error": "Screenshot capture failed — no display or capture tool available"})
        if config.max_dimension > 0:
            shot = shot.resize(config.max_dimension)
        return json.dumps(
            {
                "image_b64": shot.to_base64(),
                "width": shot.width,
                "height": shot.height,
                "urn": shot.to_urn(),
            }
        )

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Take a screenshot")


# ---------------------------------------------------------------------------
# Mouse
# ---------------------------------------------------------------------------


class MouseMoveConfig(FunctionBaseConfig, name="mouse_move"):
    pass


@register_function(config_type=MouseMoveConfig)
async def mouse_move_tool(config: MouseMoveConfig, builder):
    async def _fn(x: int, y: int) -> str:
        """Move the mouse cursor to the given (x, y) screen coordinates.

        Args:
            x: Horizontal pixel coordinate (0 = left edge)
            y: Vertical pixel coordinate (0 = top edge)

        Returns:
            JSON with success status and coordinates.
        """
        executor = DesktopActionExecutor()
        result = executor.execute("move", x=x, y=y)
        return json.dumps({"success": result.success, "x": x, "y": y, "error": result.error})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Move the mouse cursor")


class MouseClickConfig(FunctionBaseConfig, name="mouse_click"):
    pass


@register_function(config_type=MouseClickConfig)
async def mouse_click_tool(config: MouseClickConfig, builder):
    async def _fn(x: int, y: int, button: str = "left") -> str:
        """Click the mouse at the given (x, y) screen coordinates.

        Args:
            x: Horizontal pixel coordinate
            y: Vertical pixel coordinate
            button: Mouse button — "left" (default), "right", or "middle"

        Returns:
            JSON with success status.
        """
        check = _safety.check_all("click", x=x, y=y, button=button)
        if not check.safe:
            return json.dumps({"success": False, "error": f"Blocked by safety: {check.reason}"})
        executor = DesktopActionExecutor()
        result = executor.execute("click", x=x, y=y, button=button)
        return json.dumps({"success": result.success, "x": x, "y": y, "button": button, "error": result.error})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Click the mouse")


class MouseDoubleClickConfig(FunctionBaseConfig, name="mouse_double_click"):
    pass


@register_function(config_type=MouseDoubleClickConfig)
async def mouse_double_click_tool(config: MouseDoubleClickConfig, builder):
    async def _fn(x: int, y: int) -> str:
        """Double-click the mouse at the given (x, y) screen coordinates.

        Args:
            x: Horizontal pixel coordinate
            y: Vertical pixel coordinate

        Returns:
            JSON with success status.
        """
        executor = DesktopActionExecutor()
        result = executor.execute("double_click", x=x, y=y)
        return json.dumps({"success": result.success, "x": x, "y": y, "error": result.error})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Double-click the mouse")


class MouseScrollConfig(FunctionBaseConfig, name="mouse_scroll"):
    pass


@register_function(config_type=MouseScrollConfig)
async def mouse_scroll_tool(config: MouseScrollConfig, builder):
    async def _fn(x: int, y: int, delta: int = 3) -> str:
        """Scroll the mouse wheel at (x, y).

        Args:
            x: Horizontal pixel coordinate
            y: Vertical pixel coordinate
            delta: Scroll amount — positive scrolls down, negative scrolls up (default 3)

        Returns:
            JSON with success status.
        """
        executor = DesktopActionExecutor()
        result = executor.execute("scroll", x=x, y=y, delta=delta)
        return json.dumps({"success": result.success, "delta": delta, "error": result.error})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Scroll the mouse wheel")


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


class KeyboardTypeConfig(FunctionBaseConfig, name="keyboard_type"):
    pass


@register_function(config_type=KeyboardTypeConfig)
async def keyboard_type_tool(config: KeyboardTypeConfig, builder):
    async def _fn(text: str) -> str:
        """Type a string of text using the keyboard.

        Use this to fill in text fields, search bars, terminal commands, etc.
        For special keys (Enter, Tab, Escape) use keyboard_key instead.

        Args:
            text: The text string to type

        Returns:
            JSON with success status.
        """
        check = _safety.check_text(text)
        if not check.safe:
            return json.dumps({"success": False, "error": f"Blocked by safety: {check.reason}"})
        executor = DesktopActionExecutor()
        result = executor.execute("type", text=text)
        return json.dumps({"success": result.success, "error": result.error})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Type text")


class KeyboardKeyConfig(FunctionBaseConfig, name="keyboard_key"):
    pass


@register_function(config_type=KeyboardKeyConfig)
async def keyboard_key_tool(config: KeyboardKeyConfig, builder):
    async def _fn(key: str) -> str:
        """Press a single keyboard key by name.

        Common key names: Return, Escape, Tab, BackSpace, Delete,
        space, Up, Down, Left, Right, Home, End, Page_Up, Page_Down,
        F1 through F12.

        Args:
            key: Key name string (X11 keysym name)

        Returns:
            JSON with success status.
        """
        executor = DesktopActionExecutor()
        result = executor.execute("key", key=key)
        return json.dumps({"success": result.success, "key": key, "error": result.error})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Press a keyboard key")


class KeyboardHotkeyConfig(FunctionBaseConfig, name="keyboard_hotkey"):
    pass


@register_function(config_type=KeyboardHotkeyConfig)
async def keyboard_hotkey_tool(config: KeyboardHotkeyConfig, builder):
    async def _fn(keys: str) -> str:
        """Press a keyboard shortcut / key combination.

        Pass keys as a '+'-separated string, e.g.:
          "ctrl+c"         copy
          "ctrl+v"         paste
          "ctrl+z"         undo
          "alt+F4"         close window
          "ctrl+shift+t"   new tab

        Args:
            keys: '+'-separated key combo string

        Returns:
            JSON with success status.
        """
        key_list = [k.strip() for k in keys.split("+")]
        check = _safety.check_key_combo(key_list)
        if not check.safe:
            return json.dumps({"success": False, "error": f"Blocked by safety: {check.reason}"})
        executor = DesktopActionExecutor()
        result = executor.execute("hotkey", keys=key_list)
        return json.dumps({"success": result.success, "keys": keys, "error": result.error})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Press a key combination")


# ---------------------------------------------------------------------------
# Window management
# ---------------------------------------------------------------------------


class ListWindowsConfig(FunctionBaseConfig, name="list_windows"):
    pass


@register_function(config_type=ListWindowsConfig)
async def list_windows_tool(config: ListWindowsConfig, builder):
    async def _fn() -> str:
        """List all open windows with their titles, IDs, and geometry.

        Returns:
            JSON array of window objects, each with:
              - window_id: X11 window ID
              - title: window title string
              - class_name: application class name
              - pid: process ID
              - x, y: position on screen
              - width, height: window dimensions
              - active: whether this window is currently focused
        """
        mgr = WindowManager()
        windows = mgr.list_windows()
        return json.dumps([
            {
                "window_id": w.window_id,
                "title": w.title,
                "class_name": w.class_name,
                "pid": w.pid,
                "x": w.x,
                "y": w.y,
                "width": w.width,
                "height": w.height,
                "active": w.active,
            }
            for w in windows
        ])

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "List open windows")


class FocusWindowConfig(FunctionBaseConfig, name="focus_window"):
    pass


@register_function(config_type=FocusWindowConfig)
async def focus_window_tool(config: FocusWindowConfig, builder):
    async def _fn(title: str) -> str:
        """Focus a window by matching a substring of its title.

        Raises the window and gives it keyboard focus.

        Args:
            title: Substring to match against window titles (case-insensitive)

        Returns:
            JSON with success status and matched window title.
        """
        mgr = WindowManager()
        windows = mgr.search_windows(title)
        if not windows:
            return json.dumps({"success": False, "error": f"No window matching '{title}' found"})
        window = windows[0]
        result = mgr.focus_window(window.window_id)
        ok = result.get("success", False) if isinstance(result, dict) else bool(result)
        return json.dumps({"success": ok, "window_title": window.title, "window_id": window.window_id})

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Focus a window by title")


# ---------------------------------------------------------------------------
# Safety check (exposed as a tool so the agent can self-check before acting)
# ---------------------------------------------------------------------------


class CheckActionSafetyConfig(FunctionBaseConfig, name="check_action_safety"):
    pass


@register_function(config_type=CheckActionSafetyConfig)
async def check_action_safety_tool(config: CheckActionSafetyConfig, builder):
    async def _fn(action: str, params: str = "{}") -> str:
        """Check whether a proposed action is safe to execute.

        Call this before executing any action you are uncertain about.
        The safety checker validates against a blocklist of dangerous patterns.

        Args:
            action: Action type — "type", "click", "key_combo", "move", etc.
            params: JSON string of action parameters, e.g. '{"text": "rm -rf /"}'

        Returns:
            JSON with:
              - safe: boolean
              - reason: why it was blocked (if not safe)
              - warning: non-blocking warning (if any)
              - blocked: whether the action is outright blocked
              - requires_approval: whether human approval is needed
        """
        try:
            kwargs = json.loads(params)
        except json.JSONDecodeError:
            kwargs = {}
        result = _safety.check_all(action, **kwargs)
        return json.dumps(
            {
                "safe": result.safe,
                "reason": result.reason,
                "warning": result.warning,
                "blocked": result.blocked,
                "requires_approval": result.requires_approval,
            }
        )

    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__ or "Check action safety")
