"""LangChain tools for Ubuntu desktop automation.

Each function is decorated with ``@tool(parse_docstring=True)``, which infers
the JSON schema from type annotations and the ``Args:`` section of the docstring.
Import ``TOOLS`` directly — the decorated names are already ``StructuredTool`` instances.
"""
from __future__ import annotations

import subprocess

from langchain_core.tools import tool

from hermes_computer_use.safety.checker import SafetyChecker
from hermes_computer_use.tools.screenshot import (
    capture_screenshot,
    get_display_info,
    zoom_screenshot,
)
from hermes_computer_use.tools.window import WindowManager

_safety = SafetyChecker()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool(parse_docstring=True)
def take_screenshot(max_dimension: int = 0) -> str:
    """Capture a full-screen screenshot and return a base64 PNG data URI.

    Args:
        max_dimension: Max width/height in pixels. 0 means no resize.

    Returns:
        A data URI string (``data:image/png;base64,...``) or an error message.
    """
    try:
        shot = capture_screenshot(max_dimension=max_dimension)
        return f"data:image/png;base64,{shot.to_base64()}"
    except Exception as exc:
        return f"Screenshot failed: {exc}"


@tool(parse_docstring=True)
def zoom_region(x: int, y: int, width: int, height: int, output_size: int = 1024) -> str:
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


@tool(parse_docstring=True)
def click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """Click the mouse at a screen position.

    Args:
        x: Horizontal position in screen pixels.
        y: Vertical position in screen pixels.
        button: Mouse button — ``"left"`` (default), ``"right"``, or ``"middle"``.
        clicks: Number of clicks: 1 for single, 2 for double.

    Returns:
        Confirmation string or an error message.
    """
    try:
        import pyautogui as pag  # noqa: PLC0415
        if clicks == 2:
            pag.doubleClick(x, y, button=button)
        else:
            pag.click(x, y, button=button)
        return f"Clicked {button} button {clicks}x at ({x}, {y})"
    except Exception as exc:
        return f"Click failed: {exc}"


@tool(parse_docstring=True)
def move_mouse(x: int, y: int, duration: float = 0.1) -> str:
    """Move the mouse cursor to a screen position without clicking.

    Args:
        x: Horizontal position in screen pixels.
        y: Vertical position in screen pixels.
        duration: Animation duration in seconds. 0 means instant.

    Returns:
        Confirmation string or an error message.
    """
    try:
        import pyautogui as pag  # noqa: PLC0415
        pag.moveTo(x, y, duration=duration)
        return f"Moved mouse to ({x}, {y})"
    except Exception as exc:
        return f"Move failed: {exc}"


@tool(parse_docstring=True)
def scroll(x: int, y: int, amount: int) -> str:
    """Scroll the mouse wheel at a screen position.

    Args:
        x: Horizontal position in screen pixels.
        y: Vertical position in screen pixels.
        amount: Scroll distance — positive scrolls up, negative scrolls down.

    Returns:
        Confirmation string or an error message.
    """
    try:
        import pyautogui as pag  # noqa: PLC0415
        pag.scroll(amount, x=x, y=y)
        return f"Scrolled {amount} units at ({x}, {y})"
    except Exception as exc:
        return f"Scroll failed: {exc}"


@tool(parse_docstring=True)
def type_text(text: str, interval: float = 0.02) -> str:
    """Type a string of text using the keyboard.

    Args:
        text: Text to type.
        interval: Delay between keystrokes in seconds.

    Returns:
        Confirmation string, or ``"Blocked: ..."`` if the text fails safety checks.
    """
    result = _safety.check_text(text)
    if not result.safe:
        return f"Blocked: {result.reason}"
    try:
        import pyautogui as pag  # noqa: PLC0415
        pag.write(text, interval=interval)
        return f"Typed {len(text)} characters"
    except Exception as exc:
        return f"Type failed: {exc}"


@tool(parse_docstring=True)
def key_press(keys: str) -> str:
    """Press keyboard keys or hotkey combinations.

    Use ``+`` for simultaneous keys (e.g. ``ctrl+c``) and ``,`` for sequential
    presses (e.g. ``enter,enter``).

    Args:
        keys: Key or combination string. Examples: ``"enter"``, ``"ctrl+alt+t"``,
            ``"F5"``, ``"ctrl+c,ctrl+v"``.

    Returns:
        Confirmation string, or ``"Blocked: ..."`` if a combo fails safety checks.
    """
    try:
        import pyautogui as pag  # noqa: PLC0415
        for combo in keys.split(","):
            combo = combo.strip()
            parts = [p.strip() for p in combo.split("+")]
            check = _safety.check_key_combo(parts)
            if not check.safe:
                return f"Blocked: {check.reason}"
            if len(parts) == 1:
                pag.press(parts[0])
            else:
                pag.hotkey(*parts)
        return f"Pressed keys: {keys}"
    except Exception as exc:
        return f"Key press failed: {exc}"


@tool(parse_docstring=True)
def list_windows() -> str:
    """List all visible windows currently open on the desktop.

    Returns:
        Newline-separated list of ``window_id  title  geometry`` entries,
        or ``"No windows found."`` if the desktop is empty.
    """
    try:
        windows = WindowManager().list_windows()
        if not windows:
            return "No windows found."
        return "\n".join(f"{w.window_id}  {w.title!r}  {w.geometry}" for w in windows)
    except Exception as exc:
        return f"list_windows failed: {exc}"


@tool(parse_docstring=True)
def focus_window(window_id: str) -> str:
    """Bring a window to the foreground.

    Args:
        window_id: Window ID string as returned by ``list_windows``.

    Returns:
        Confirmation string or an error message.
    """
    try:
        result = WindowManager().focus_window(window_id)
        if result.get("status") == "success":
            return f"Focused window {window_id}"
        return f"focus_window failed: {result.get('message', 'unknown error')}"
    except Exception as exc:
        return f"focus_window failed: {exc}"


@tool(parse_docstring=True)
def run_command(command: str, timeout: int = 30) -> str:
    """Run a shell command with ``bash -c`` and return its stdout + stderr.

    Args:
        command: Shell command to execute.
        timeout: Maximum seconds to wait before killing the process.

    Returns:
        Combined stdout/stderr output, exit code notice, or an error message.
    """
    check = _safety.check_text(command)
    if not check.safe:
        return f"Command blocked: {check.reason}"
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


@tool(parse_docstring=True)
def get_screen_info() -> str:
    """Get current screen resolution and display server info (X11/Wayland/none).

    Returns:
        Newline-separated key=value pairs: ``server_type``, ``display``,
        and (when a display is active) ``width`` and ``height``.
    """
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
# Tool list — import this in agent.py
# ---------------------------------------------------------------------------

TOOLS = [
    take_screenshot,
    zoom_region,
    click,
    move_mouse,
    scroll,
    type_text,
    key_press,
    list_windows,
    focus_window,
    run_command,
    get_screen_info,
]
