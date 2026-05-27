"""Screenshot capture — cross-platform screen capture for desktop automation."""

from __future__ import annotations

import base64
import io
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from PIL import Image

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
        img = Image.open(io.BytesIO(self.data)).convert("RGB")
        if max(self.width, self.height) <= max_dimension:
            return self  # No resize needed

        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
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
        max_dimension: Maximum width or height for the output image. Pass 0 to disable resizing.

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
                # Resize if needed (max_dimension=0 means no cap)
                if max_dimension > 0 and max(screenshot.width, screenshot.height) > max_dimension:
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
    cmd = ["scrot", f"/tmp/hermes_screenshot_{os.getpid()}.png", "--silent"]

    if region:
        x, y, w, h = region
        cmd = [
            "scrot",
            f"/tmp/hermes_screenshot_{os.getpid()}.png",
            "--silent",
            "-a",
            f"{x},{y},{w},{h}",
        ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=10, check=True)
        path = f"/tmp/hermes_screenshot_{os.getpid()}.png"

        with open(path, "rb") as f:
            data = f.read()

        img = Image.open(io.BytesIO(data))
        return Screenshot(data=data, width=img.width, height=img.height)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _capture_xdotool(region: tuple[int, int, int, int] | None) -> Screenshot | None:
    """Capture using xwd + convert (ImageMagick) via xdotool."""
    try:
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
        import pyautogui  # noqa: PLC0415 — deferred: connecting to display on import breaks headless tests

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


def zoom_screenshot(
    x: int,
    y: int,
    width: int,
    height: int,
    output_size: int = 1024,
) -> Screenshot:
    """Capture a region of the screen and upscale it to output_size pixels.

    Crops the screen to the given rectangle, then upscales the crop so the
    longest edge equals output_size. The result is a high-resolution close-up
    of that region — useful for reading small text, inspecting UI elements, or
    verifying form fields after a full-screen screenshot showed something
    ambiguous.

    Args:
        x: Left edge of the region in screen coordinates.
        y: Top edge of the region in screen coordinates.
        width: Width of the region in pixels.
        height: Height of the region in pixels.
        output_size: Target size for the longest edge of the output image
            (default 1024). The image is always upscaled to fill this, even
            if the source region is smaller.

    Returns:
        Screenshot of the zoomed region, with width/height reflecting the
        upscaled dimensions.

    Raises:
        ValueError: If width or height is <= 0.
        RuntimeError: If no display server is available or capture fails.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Region dimensions must be positive, got {width}x{height}")

    # Capture exactly the requested region (no max_dimension cap — we want
    # raw pixels so we can upscale deliberately below).
    shot = capture_screenshot(region=(x, y, width, height), max_dimension=0)

    img = Image.open(io.BytesIO(shot.data)).convert("RGB")

    # Always scale UP to output_size so the caller gets a large, readable image.
    scale = output_size / max(img.width, img.height)
    new_w = max(1, round(img.width * scale))
    new_h = max(1, round(img.height * scale))
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Screenshot(
        data=buf.read(),
        width=new_w,
        height=new_h,
        scale_factor=scale,
    )


def get_screen_size() -> tuple[int, int]:
    """Get the primary display resolution."""
    screenshot = capture_screenshot()
    return screenshot.width, screenshot.height
