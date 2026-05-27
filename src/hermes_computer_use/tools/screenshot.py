"""Screenshot capture — cross-platform screen capture for desktop automation."""

from __future__ import annotations

import base64
import io
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Screenshot:
    """Captured screenshot with metadata."""

    data: bytes  # Raw PNG bytes
    width: int
    height: int
    scale_factor: float = 1.0

    def to_base64(self) -> str:
        """Encode as base64 for transmission to vision APIs."""
        return base64.b64encode(self.data).decode("utf-8")

    def to_urn(self) -> str:
        """Create a data: URN for vision model APIs."""
        return f"data:image/png;base64,{self.to_base64()}"

    def resize(self, max_dimension: int = 1024) -> Screenshot:
        """Resize screenshot to fit within max_dimension while maintaining aspect ratio."""
        from PIL import Image

        img = Image.open(io.BytesIO(self.data)).convert("RGB")
        if max(self.width, self.height) <= max_dimension:
            return self  # No resize needed

        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return Screenshot(
            data=buf.read(),
            width=img.width,
            height=img.height,
            scale_factor=max_dimension / max(self.width, self.height),
        )


def get_display_info() -> dict[str, Any]:
    """Detect display configuration."""
    display = os.environ.get("DISPLAY", "")
    wayland = os.environ.get("WAYLAND_DISPLAY", "")

    info: dict[str, Any] = {"display": display, "wayland": bool(wayland)}

    if wayland:
        info["server_type"] = "wayland"
    elif display:
        info["server_type"] = "x11"
    else:
        info["server_type"] = "none"

    return info


def capture_screenshot(
    region: tuple[int, int, int, int] | None = None,
    max_dimension: int = 1024,
) -> Screenshot:
    """Capture a screenshot of the screen.

    Supports multiple capture methods:
    1. scrot (primary, lightweight)
    2. gnome-screenshot (GNOME desktop)
    3. xwd (X11 raw format, convert with convert)
    4. PyAutoGUI (fallback)

    Args:
        region: Optional (x, y, width, height) to capture only part of the screen.
        max_dimension: Maximum width or height for the output image.

    Returns:
        Screenshot with PNG data, dimensions, and metadata.

    Raises:
        RuntimeError: If no display server is available or capture fails.
    """
    server_type = get_display_info()["server_type"]

    if server_type == "none":
        raise RuntimeError(
            "No display server detected. Set DISPLAY or run on a desktop system."
        )

    # Try capture methods in order of preference
    for method in [_capture_scrot, _capture_xdotool, _capture_pyautogui]:
        try:
            screenshot = method(region)
            if screenshot:
                # Resize if needed
                if max(screenshot.width, screenshot.height) > max_dimension:
                    screenshot = screenshot.resize(max_dimension)
                return screenshot
        except Exception as exc:
            logger.debug("Screenshot method %s failed: %s", method.__name__, exc)
            continue

    raise RuntimeError(
        "Screenshot capture failed. Install scrot or xdotool, or ensure DISPLAY is set."
    )


def _capture_scrot(region: tuple[int, int, int, int] | None) -> Screenshot | None:
    """Capture using scrot (Simple Camera Robot)."""
    cmd = ["scrot", "/tmp/hermes_screenshot_{}.png".format(os.getpid()), "--silent"]

    if region:
        x, y, w, h = region
        cmd = [
            "scrot",
            "/tmp/hermes_screenshot_{}.png".format(os.getpid()),
            "--silent",
            "-a",
            f"{x},{y},{w},{h}",
        ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=10, check=True
        )
        path = cmd[-2] if region else cmd[-1]
        # Remove the filename from the command list
        if region:
            path = "/tmp/hermes_screenshot_{}.png".format(os.getpid())
        else:
            path = "/tmp/hermes_screenshot_{}.png".format(os.getpid())

        with open(path, "rb") as f:
            data = f.read()

        from PIL import Image

        img = Image.open(io.BytesIO(data))
        return Screenshot(data=data, width=img.width, height=img.height)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _capture_xdotool(region: tuple[int, int, int, int] | None) -> Screenshot | None:
    """Capture using xwd + convert (ImageMagick) via xdotool."""
    try:
        from PIL import Image

        if region:
            x, y, w, h = region
            # Use xwd to capture region
            result = subprocess.run(
                ["xwd", "-root", "-window", "root", "-out", f"/tmp/hermes_screenshot_{os.getpid()}.xwd",
                 "-geometry", f"{w}x{h}+{x}+{y}"],
                capture_output=True, timeout=10, check=False
            )
            if result.returncode != 0:
                return None
            # Convert xwd to PNG
            subprocess.run(
                ["convert", f"/tmp/hermes_screenshot_{os.getpid()}.xwd",
                 f"/tmp/hermes_screenshot_{os.getpid()}.png"],
                capture_output=True, timeout=10, check=False
            )
            path = f"/tmp/hermes_screenshot_{os.getpid()}.png"
        else:
            result = subprocess.run(
                ["xwd", "-root", "-window", "root", "-out", f"/tmp/hermes_screenshot_{os.getpid()}.xwd"],
                capture_output=True, timeout=10, check=False
            )
            if result.returncode != 0:
                return None
            subprocess.run(
                ["convert", f"/tmp/hermes_screenshot_{os.getpid()}.xwd",
                 f"/tmp/hermes_screenshot_{os.getpid()}.png"],
                capture_output=True, timeout=10, check=False
            )
            path = f"/tmp/hermes_screenshot_{os.getpid()}.png"

        if not os.path.exists(path):
            return None

        with open(path, "rb") as f:
            data = f.read()

        img = Image.open(io.BytesIO(data))
        return Screenshot(data=data, width=img.width, height=img.height)

    except (FileNotFoundError, OSError):
        return None


def _capture_pyautogui(region: tuple[int, int, int, int] | None) -> Screenshot | None:
    """Capture using PyAutoGUI as a fallback."""
    try:
        import pyautogui

        # PyAutoGUI doesn't support regions directly, so we crop afterwards
        if region:
            x, y, w, h = region
            img = pyautogui.screenshot()
            img = img.crop((x, y, x + w, y + h))
        else:
            img = pyautogui.screenshot()

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return Screenshot(
            data=buf.read(),
            width=img.width,
            height=img.height,
        )
    except Exception:
        return None


def get_screen_size() -> tuple[int, int]:
    """Get the primary display resolution."""
    screenshot = capture_screenshot()
    return screenshot.width, screenshot.height
