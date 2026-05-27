"""NAT tool registrations for Ubuntu desktop automation.

Each tool is a ``@register_function``-decorated async generator that yields a
``FunctionInfo``.  The inner async callable is the actual tool implementation.
NAT's ``react_agent`` discovers tools by their ``name=`` field on the config
class and passes them to the LLM as callable tools.

Tool names (used in workflow.yaml ``tool_names`` list):
    take_screenshot, zoom_region, click, move_mouse, type_text,
    key_press, scroll, run_command, list_windows, focus_window, get_screen_info

NAT quirks encoded here:
- ``FunctionInfo.from_fn`` requires exactly 1 parameter on the inner function.
  Multi-param functions are handled by NAT automatically (it wraps them).
  Zero-param functions must use a dummy ``_unused: str = ""`` parameter.
- Tool discovery uses Python entry points (group ``nat.plugins``), NOT workflow.yaml.
  Register in pyproject.toml: ``[project.entry-points."nat.plugins"]``
"""
from __future__ import annotations

import json
import subprocess

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from hermes_computer_use.helpers.screenshot import (
    capture_screenshot,
    get_display_info,
    zoom_screenshot,
)
from hermes_computer_use.helpers.window import WindowManager


# ---------------------------------------------------------------------------
# Config sentinels — each must have a unique name= that matches workflow.yaml
# ---------------------------------------------------------------------------

class TakeScreenshotConfig(FunctionBaseConfig, name="take_screenshot"):
    """Capture a full-screen screenshot and return a base64 PNG data URI."""


class ZoomRegionConfig(FunctionBaseConfig, name="zoom_region"):
    """Zoom into a rectangular region of the screen and return a base64 PNG."""


class ClickConfig(FunctionBaseConfig, name="click"):
    """Click the mouse at a screen position."""


class MoveMouthConfig(FunctionBaseConfig, name="move_mouse"):
    """Move the mouse cursor to a screen position without clicking."""


class TypeTextConfig(FunctionBaseConfig, name="type_text"):
    """Type a string of text using the keyboard."""


class KeyPressConfig(FunctionBaseConfig, name="key_press"):
    """Press one or more keyboard keys (supports hotkeys)."""


class ScrollConfig(FunctionBaseConfig, name="scroll"):
    """Scroll the mouse wheel at a screen position."""


class RunCommandConfig(FunctionBaseConfig, name="run_command"):
    """Run a shell command and return its stdout/stderr."""


class ListWindowsConfig(FunctionBaseConfig, name="list_windows"):
    """List all visible windows on the desktop."""


class FocusWindowConfig(FunctionBaseConfig, name="focus_window"):
    """Focus (raise and activate) a window by title."""


class GetScreenInfoConfig(FunctionBaseConfig, name="get_screen_info"):
    """Return display server info (type, resolution, DISPLAY env var)."""


# ---------------------------------------------------------------------------
# Tool registrations
# ---------------------------------------------------------------------------

@register_function(config_type=TakeScreenshotConfig)
async def take_screenshot(_config: TakeScreenshotConfig, _builder: Builder):
    """NAT tool: capture a full-screen screenshot."""

    async def _impl(max_dimension: int = 0) -> str:
        """Capture a full-screen screenshot and return a base64 PNG data URI.

        Args:
            max_dimension: Max width/height in pixels. 0 means no resize.

        Returns:
            A data URI string ``data:image/png;base64,...`` or an error message.
        """
        try:
            shot = capture_screenshot(max_dimension=max_dimension)
            return f"data:image/png;base64,{shot.to_base64()}"
        except Exception as exc:
            return f"Screenshot failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=TakeScreenshotConfig.__doc__)


@register_function(config_type=ZoomRegionConfig)
async def zoom_region(_config: ZoomRegionConfig, _builder: Builder):
    """NAT tool: zoom into a rectangular region of the screen."""

    async def _impl(x: int, y: int, width: int, height: int, output_size: int = 1024) -> str:
        """Zoom into a rectangular region of the screen and return a base64 PNG.

        Use this to read small text or inspect UI elements closely.

        Args:
            x: Left edge of the region in screen pixels.
            y: Top edge of the region in screen pixels.
            width: Width of the region in pixels.
            height: Height of the region in pixels.
            output_size: Target size for the longest edge in the output image.

        Returns:
            A data URI string or an error message.
        """
        try:
            shot = zoom_screenshot(x=x, y=y, width=width, height=height, output_size=output_size)
            return f"data:image/png;base64,{shot.to_base64()}"
        except Exception as exc:
            return f"Zoom failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=ZoomRegionConfig.__doc__)


@register_function(config_type=ClickConfig)
async def click(_config: ClickConfig, _builder: Builder):
    """NAT tool: click the mouse at a screen position."""

    async def _impl(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        """Click the mouse at a screen position.

        Args:
            x: Horizontal position in screen pixels.
            y: Vertical position in screen pixels.
            button: Mouse button — ``left`` (default), ``right``, or ``middle``.
            clicks: Number of clicks: 1 for single, 2 for double.

        Returns:
            Confirmation string or an error message.
        """
        try:
            import pyautogui as pag  # noqa: PLC0415
            if clicks == 2:
                pag.doubleClick(x=x, y=y, button=button)
            else:
                pag.click(x=x, y=y, button=button, clicks=clicks)
            return f"Clicked {button} at ({x}, {y}) × {clicks}"
        except Exception as exc:
            return f"Click failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=ClickConfig.__doc__)


@register_function(config_type=MoveMouthConfig)
async def move_mouse(_config: MoveMouthConfig, _builder: Builder):
    """NAT tool: move the mouse cursor without clicking."""

    async def _impl(x: int, y: int) -> str:
        """Move the mouse cursor to a screen position without clicking.

        Args:
            x: Horizontal position in screen pixels.
            y: Vertical position in screen pixels.

        Returns:
            Confirmation string or an error message.
        """
        try:
            import pyautogui as pag  # noqa: PLC0415
            pag.moveTo(x=x, y=y)
            return f"Mouse moved to ({x}, {y})"
        except Exception as exc:
            return f"Move failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=MoveMouthConfig.__doc__)


@register_function(config_type=TypeTextConfig)
async def type_text(_config: TypeTextConfig, _builder: Builder):
    """NAT tool: type a string using the keyboard."""

    async def _impl(text: str, interval: float = 0.02) -> str:
        """Type a string of text using the keyboard.

        Args:
            text: The text to type.
            interval: Delay between keystrokes in seconds.

        Returns:
            Confirmation string or an error message.
        """
        try:
            import pyautogui as pag  # noqa: PLC0415
            pag.typewrite(text, interval=interval)
            return f"Typed {len(text)} characters"
        except Exception as exc:
            return f"Type failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=TypeTextConfig.__doc__)


@register_function(config_type=KeyPressConfig)
async def key_press(_config: KeyPressConfig, _builder: Builder):
    """NAT tool: press one or more keyboard keys."""

    async def _impl(keys: str) -> str:
        """Press one or more keyboard keys (supports hotkeys like ctrl+c).

        Args:
            keys: Key name or hotkey combo, e.g. ``enter``, ``ctrl+c``,
                  ``alt+F4``, ``ctrl+shift+t``.

        Returns:
            Confirmation string or an error message.
        """
        try:
            import pyautogui as pag  # noqa: PLC0415
            parts = [k.strip() for k in keys.split("+")]
            if len(parts) > 1:
                pag.hotkey(*parts)
            else:
                pag.press(parts[0])
            return f"Pressed: {keys}"
        except Exception as exc:
            return f"Key press failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=KeyPressConfig.__doc__)


@register_function(config_type=ScrollConfig)
async def scroll(_config: ScrollConfig, _builder: Builder):
    """NAT tool: scroll the mouse wheel."""

    async def _impl(x: int, y: int, clicks: int = 3, direction: str = "down") -> str:
        """Scroll the mouse wheel at a screen position.

        Args:
            x: Horizontal position in screen pixels.
            y: Vertical position in screen pixels.
            clicks: Number of scroll increments (default 3).
            direction: ``down`` (default) or ``up``.

        Returns:
            Confirmation string or an error message.
        """
        try:
            import pyautogui as pag  # noqa: PLC0415
            amount = -clicks if direction == "down" else clicks
            pag.scroll(amount, x=x, y=y)
            return f"Scrolled {direction} {clicks} clicks at ({x}, {y})"
        except Exception as exc:
            return f"Scroll failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=ScrollConfig.__doc__)


@register_function(config_type=RunCommandConfig)
async def run_command(_config: RunCommandConfig, _builder: Builder):
    """NAT tool: run a shell command."""

    async def _impl(command: str, timeout: int = 30) -> str:
        """Run a shell command and return its combined stdout and stderr.

        Args:
            command: The shell command to run (executed via ``/bin/bash -c``).
            timeout: Maximum execution time in seconds (default 30).

        Returns:
            Combined stdout/stderr or an error message on failure.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            if result.returncode != 0:
                output += f"\nExit code: {result.returncode}"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"
        except Exception as exc:
            return f"Command failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=RunCommandConfig.__doc__)


@register_function(config_type=ListWindowsConfig)
async def list_windows(_config: ListWindowsConfig, _builder: Builder):
    """NAT tool: list visible windows on the desktop."""

    # NAT requires ≥1 parameter; this tool takes none, so we add a dummy.
    async def _impl(unused: str = "") -> str:
        """List all visible windows on the desktop.

        Args:
            unused: Ignored. Pass an empty string or omit.

        Returns:
            JSON-formatted list of window info dicts, or an error message.
        """
        try:
            wm = WindowManager()
            windows = wm.list_windows()
            return json.dumps(windows, indent=2)
        except Exception as exc:
            return f"List windows failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=ListWindowsConfig.__doc__)


@register_function(config_type=FocusWindowConfig)
async def focus_window(_config: FocusWindowConfig, _builder: Builder):
    """NAT tool: focus a window by title."""

    async def _impl(title: str) -> str:
        """Focus (raise and activate) a window by title substring match.

        Args:
            title: Substring of the window title to match (case-insensitive).

        Returns:
            Confirmation string or an error message.
        """
        try:
            wm = WindowManager()
            result = wm.focus_window(title)
            return result
        except Exception as exc:
            return f"Focus window failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=FocusWindowConfig.__doc__)


@register_function(config_type=GetScreenInfoConfig)
async def get_screen_info(_config: GetScreenInfoConfig, _builder: Builder):
    """NAT tool: return display server info."""

    # NAT requires ≥1 parameter; this tool takes none, so we add a dummy.
    async def _impl(unused: str = "") -> str:
        """Return display server info (type, resolution, DISPLAY env var).

        Args:
            unused: Ignored. Pass an empty string or omit.

        Returns:
            JSON-formatted dict with keys: display, server_type, width, height.
        """
        try:
            info = get_display_info()
            return json.dumps(info, indent=2)
        except Exception as exc:
            return f"Get screen info failed: {exc}"

    yield FunctionInfo.from_fn(_impl, description=GetScreenInfoConfig.__doc__)
