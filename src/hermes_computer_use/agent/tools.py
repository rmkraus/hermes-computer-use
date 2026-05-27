"""LangChain tool wrappers for Ubuntu desktop automation.

Tools are created via ``get_computer_use_tools(safety_checker)`` which
returns a fresh list of StructuredTool instances bound to the given
SafetyChecker.  This keeps tests fully isolated (each test gets its own
checker) while letting the server share a single long-lived instance.

Heavy imports (pyautogui) are deferred to call time so importing this
module never triggers a display connection.
"""
from __future__ import annotations

import subprocess

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from hermes_computer_use.safety.checker import SafetyChecker
from hermes_computer_use.tools.screenshot import (
    capture_screenshot,
    get_display_info,
    zoom_screenshot,
)
from hermes_computer_use.tools.window import WindowManager


# ---------------------------------------------------------------------------
# Input schemas (Pydantic v2)
# ---------------------------------------------------------------------------


class TakeScreenshotInput(BaseModel):
    max_dimension: int = Field(default=0, description="Max width/height in pixels (0 = no resize).")


class ZoomRegionInput(BaseModel):
    x: int = Field(description="Left edge of region in screen pixels.")
    y: int = Field(description="Top edge of region in screen pixels.")
    width: int = Field(description="Width of region in pixels.")
    height: int = Field(description="Height of region in pixels.")
    output_size: int = Field(default=1024, description="Target size for longest edge.")


class ClickInput(BaseModel):
    x: int = Field(description="Horizontal position in screen pixels.")
    y: int = Field(description='Vertical position in screen pixels.')
    button: str = Field(default="left", description='"left", "right", or "middle".')
    clicks: int = Field(default=1, description="1 = single click, 2 = double click.")


class MoveMouseInput(BaseModel):
    x: int = Field(description="Horizontal position in screen pixels.")
    y: int = Field(description="Vertical position in screen pixels.")
    duration: float = Field(default=0.1, description="Animation duration in seconds (0 = instant).")


class ScrollInput(BaseModel):
    x: int = Field(description="Horizontal position in screen pixels.")
    y: int = Field(description="Vertical position in screen pixels.")
    amount: int = Field(description="Scroll distance — positive = up, negative = down.")


class TypeTextInput(BaseModel):
    text: str = Field(description="Text to type.")
    interval: float = Field(default=0.02, description="Delay between keystrokes in seconds.")


class KeyPressInput(BaseModel):
    keys: str = Field(
        description=(
            "Key or combination string.  Use + for simultaneous keys (e.g. 'ctrl+c'), "
            "comma for sequential (e.g. 'enter,enter').  Examples: 'enter', 'ctrl+alt+t', 'F5'."
        )
    )


class ListWindowsInput(BaseModel):
    pass


class FocusWindowInput(BaseModel):
    window_id: str = Field(description="Window ID string as returned by list_windows.")


class RunCommandInput(BaseModel):
    command: str = Field(description="Shell command to run with bash -c.")
    timeout: int = Field(default=30, description="Maximum seconds to wait.")


class GetScreenInfoInput(BaseModel):
    pass


# ---------------------------------------------------------------------------
# Implementation functions (accept safety as first positional arg)
# ---------------------------------------------------------------------------


def _take_screenshot(safety: SafetyChecker, max_dimension: int = 0) -> str:
    safety.record_action()
    try:
        screenshot = capture_screenshot(max_dimension=max_dimension)
        return f"data:image/png;base64,{screenshot.to_base64()}"
    except Exception as exc:
        return f"Screenshot failed: {exc}"


def _zoom_region(
    safety: SafetyChecker,
    x: int,
    y: int,
    width: int,
    height: int,
    output_size: int = 1024,
) -> str:
    safety.record_action()
    try:
        screenshot = zoom_screenshot(x=x, y=y, width=width, height=height, output_size=output_size)
        return f"data:image/png;base64,{screenshot.to_base64()}"
    except Exception as exc:
        return f"Zoom failed: {exc}"


def _click(
    safety: SafetyChecker,
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> str:
    safety.record_action()
    try:
        import pyautogui as pag  # noqa: PLC0415
        if clicks == 2:
            pag.doubleClick(x, y, button=button)
        else:
            pag.click(x, y, button=button)
        return f"Clicked {button} button {clicks}x at ({x}, {y})"
    except Exception as exc:
        return f"Click failed: {exc}"


def _move_mouse(
    safety: SafetyChecker,
    x: int,
    y: int,
    duration: float = 0.1,
) -> str:
    safety.record_action()
    try:
        import pyautogui as pag  # noqa: PLC0415
        pag.moveTo(x, y, duration=duration)
        return f"Moved mouse to ({x}, {y})"
    except Exception as exc:
        return f"Move failed: {exc}"


def _scroll(safety: SafetyChecker, x: int, y: int, amount: int) -> str:
    safety.record_action()
    try:
        import pyautogui as pag  # noqa: PLC0415
        pag.scroll(amount, x=x, y=y)
        return f"Scrolled {amount} units at ({x}, {y})"
    except Exception as exc:
        return f"Scroll failed: {exc}"


def _type_text(safety: SafetyChecker, text: str, interval: float = 0.02) -> str:
    result = safety.check_text(text)
    if not result.safe:
        return f"Blocked: {result.reason}"
    safety.record_action()
    try:
        import pyautogui as pag  # noqa: PLC0415
        pag.write(text, interval=interval)
        return f"Typed {len(text)} characters"
    except Exception as exc:
        return f"Type failed: {exc}"


def _key_press(safety: SafetyChecker, keys: str) -> str:
    safety.record_action()
    try:
        import pyautogui as pag  # noqa: PLC0415
        for combo in keys.split(","):
            combo = combo.strip()
            parts = [p.strip() for p in combo.split("+")]
            check = safety.check_key_combo(parts)
            if not check.safe:
                return f"Blocked: {check.reason}"
            if len(parts) == 1:
                pag.press(parts[0])
            else:
                pag.hotkey(*parts)
        return f"Pressed keys: {keys}"
    except Exception as exc:
        return f"Key press failed: {exc}"


def _list_windows(safety: SafetyChecker) -> str:
    safety.record_action()
    try:
        wm = WindowManager()
        windows = wm.list_windows()
        if not windows:
            return "No windows found."
        return "\n".join(f"{w.window_id}  {w.title!r}  {w.geometry}" for w in windows)
    except Exception as exc:
        return f"list_windows failed: {exc}"


def _focus_window(safety: SafetyChecker, window_id: str) -> str:
    safety.record_action()
    try:
        wm = WindowManager()
        result = wm.focus_window(window_id)
        if result.get("status") == "success":
            return f"Focused window {window_id}"
        return f"focus_window failed: {result.get('message', 'unknown error')}"
    except Exception as exc:
        return f"focus_window failed: {exc}"


def _run_command(safety: SafetyChecker, command: str, timeout: int = 30) -> str:
    check = safety.check_text(command)
    if not check.safe:
        return f"Command blocked: {check.reason}"
    safety.record_action()
    try:
        result = subprocess.run(  # noqa: S603
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else f"(exit code {result.returncode})"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s: {command}"
    except Exception as exc:
        return f"Command failed: {exc}"


def _get_screen_info(safety: SafetyChecker) -> str:
    safety.record_action()
    info = get_display_info()
    server = info.get("server_type", "none")
    display = info.get("display", "")
    lines = [f"server_type={server}", f"display={display}"]
    if server != "none":
        try:
            shot = capture_screenshot(max_dimension=0)
            lines += [f"width={shot.width}", f"height={shot.height}"]
        except Exception:
            pass
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def get_computer_use_tools(safety_checker: SafetyChecker | None = None) -> list:
    """Return all computer-use LangChain tools bound to a SafetyChecker.

    Creates a fresh list of StructuredTool instances on each call.
    Pass a custom ``safety_checker`` for test isolation.

    Args:
        safety_checker: Override the default module-level SafetyChecker.

    Returns:
        List of LangChain StructuredTool instances.
    """
    checker = safety_checker or SafetyChecker()

    # Use closures (not functools.partial) so get_type_hints() works on the
    # wrapper functions.  LangGraph's ToolNode calls get_type_hints() to
    # resolve injected args and partial objects are not introspectable modules.

    def take_screenshot(max_dimension: int = 0) -> str:
        return _take_screenshot(checker, max_dimension)

    def zoom_region(x: int, y: int, width: int, height: int, output_size: int = 1024) -> str:
        return _zoom_region(checker, x, y, width, height, output_size)

    def click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        return _click(checker, x, y, button, clicks)

    def move_mouse(x: int, y: int, duration: float = 0.1) -> str:
        return _move_mouse(checker, x, y, duration)

    def scroll(x: int, y: int, amount: int) -> str:
        return _scroll(checker, x, y, amount)

    def type_text(text: str, interval: float = 0.02) -> str:
        return _type_text(checker, text, interval)

    def key_press(keys: str) -> str:
        return _key_press(checker, keys)

    def list_windows() -> str:
        return _list_windows(checker)

    def focus_window(window_id: str) -> str:
        return _focus_window(checker, window_id)

    def run_command(command: str, timeout: int = 30) -> str:
        return _run_command(checker, command, timeout)

    def get_screen_info() -> str:
        return _get_screen_info(checker)

    return [
        StructuredTool.from_function(
            func=take_screenshot,
            name="take_screenshot",
            description="Capture a full-screen screenshot and return a base64 PNG data URI.",
            args_schema=TakeScreenshotInput,
        ),
        StructuredTool.from_function(
            func=zoom_region,
            name="zoom_region",
            description=(
                "Zoom into a rectangular region of the screen and return a base64 PNG. "
                "Use this to read small text or inspect UI elements closely."
            ),
            args_schema=ZoomRegionInput,
        ),
        StructuredTool.from_function(
            func=click,
            name="click",
            description=(
                'Click the mouse at a screen position. '
                'button: "left" (default), "right", or "middle". '
                'clicks: 1 = single, 2 = double.'
            ),
            args_schema=ClickInput,
        ),
        StructuredTool.from_function(
            func=move_mouse,
            name="move_mouse",
            description="Move the mouse cursor to a screen position without clicking.",
            args_schema=MoveMouseInput,
        ),
        StructuredTool.from_function(
            func=scroll,
            name="scroll",
            description="Scroll the mouse wheel. Positive amount = up, negative = down.",
            args_schema=ScrollInput,
        ),
        StructuredTool.from_function(
            func=type_text,
            name="type_text",
            description="Type a string of text using the keyboard.",
            args_schema=TypeTextInput,
        ),
        StructuredTool.from_function(
            func=key_press,
            name="key_press",
            description=(
                "Press keyboard keys or hotkey combinations. "
                "Use + for simultaneous (ctrl+c), comma for sequential (enter,enter)."
            ),
            args_schema=KeyPressInput,
        ),
        StructuredTool.from_function(
            func=list_windows,
            name="list_windows",
            description="List all visible windows currently open on the desktop.",
            args_schema=ListWindowsInput,
        ),
        StructuredTool.from_function(
            func=focus_window,
            name="focus_window",
            description="Bring a window to the foreground. Use window_id from list_windows.",
            args_schema=FocusWindowInput,
        ),
        StructuredTool.from_function(
            func=run_command,
            name="run_command",
            description="Run a shell command (bash -c) and return its stdout + stderr output.",
            args_schema=RunCommandInput,
        ),
        StructuredTool.from_function(
            func=get_screen_info,
            name="get_screen_info",
            description="Get current screen resolution and display server info (X11/Wayland/none).",
            args_schema=GetScreenInfoInput,
        ),
    ]

