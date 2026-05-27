"""Window management — list, focus, and manage open windows."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """Information about an open window."""

    window_id: str
    title: str
    class_name: str
    pid: int
    x: int
    y: int
    width: int
    height: int
    active: bool = False

    @property
    def geometry(self) -> str:
        """Format geometry as X11-style string (WIDTHxHEIGHT+X+Y)."""
        return f"{self.width}x{self.height}+{self.x}+{self.y}"


@dataclass
class WindowManager:
    """Window management engine.

    Uses xdotool as the primary backend for X11 window management.
    Provides listing, focusing, and information about open windows.
    """

    def __init__(self) -> None:
        """Initialize the window manager."""
        self._xdotool_available = self._check_xdotool()

    def _check_xdotool(self) -> bool:
        """Check if xdotool is available."""
        try:
            result = subprocess.run(
                ["xdotool", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False

    def list_windows(self) -> list[WindowInfo]:
        """List all open windows.

        Returns:
            List of WindowInfo for all open windows.
        """
        if not self._xdotool_available:
            logger.warning("xdotool not available, cannot list windows")
            return []

        try:
            # Get all window IDs
            result = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", "."],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            window_ids = result.stdout.strip().split("\n")
            windows = []

            for wid in window_ids:
                wid = wid.strip()
                if not wid:
                    continue

                window_info = self._get_window_info(wid)
                if window_info:
                    windows.append(window_info)

            return windows

        except subprocess.TimeoutExpired:
            return []

    def _get_window_info(self, window_id: str) -> WindowInfo | None:
        """Get detailed information about a single window.

        Args:
            window_id: Window ID string.

        Returns:
            WindowInfo or None if window doesn't exist.
        """
        try:
            # Get window properties
            info: dict[str, Any] = {}

            # Window title
            result = subprocess.run(
                ["xdotool", "getwindowname", window_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            info["title"] = result.stdout.strip() if result.returncode == 0 else ""

            # Window class
            result = subprocess.run(
                ["xdotool", "getwindowclass", window_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            info["class"] = result.stdout.strip() if result.returncode == 0 else ""

            # PID
            result = subprocess.run(
                ["xdotool", "getwindowpid", window_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            info["pid"] = int(result.stdout.strip()) if result.returncode == 0 else 0

            # Geometry
            result = subprocess.run(
                ["xdotool", "getwindowgeometry", "--shell", window_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            geometry: dict[str, str] = {}
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        geometry[key.strip()] = value.strip()

            return WindowInfo(
                window_id=window_id,
                title=info.get("title", ""),
                class_name=info.get("class", ""),
                pid=info.get("pid", 0),
                x=int(geometry.get("X", 0)),
                y=int(geometry.get("Y", 0)),
                width=int(geometry.get("WIDTH", 0)),
                height=int(geometry.get("HEIGHT", 0)),
            )

        except (subprocess.TimeoutExpired, ValueError, KeyError):
            return None

    def focus_window(self, window_id: str) -> dict[str, Any]:
        """Focus a window by ID.

        Args:
            window_id: Window ID to focus.

        Returns:
            Result dict with status.
        """
        if not self._xdotool_available:
            return {"status": "error", "message": "xdotool not available"}

        try:
            subprocess.run(
                ["xdotool", "windowfocus", "--window", window_id],
                capture_output=True,
                timeout=10,
                check=True,
            )

            return {
                "action": "focus_window",
                "window_id": window_id,
                "status": "success",
            }

        except subprocess.CalledProcessError:
            return {
                "action": "focus_window",
                "window_id": window_id,
                "status": "error",
                "message": "Failed to focus window",
            }
        except subprocess.TimeoutExpired:
            return {
                "action": "focus_window",
                "window_id": window_id,
                "status": "error",
                "message": "Window focus timed out",
            }

    def search_windows(self, search_term: str) -> list[WindowInfo]:
        """Search for windows by title or class.

        Args:
            search_term: Text to search for in window titles/classes.

        Returns:
            List of matching WindowInfo objects.
        """
        if not self._xdotool_available:
            return []

        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", search_term],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            window_ids = result.stdout.strip().split("\n")
            windows = []

            for wid in window_ids:
                wid = wid.strip()
                if wid:
                    window_info = self._get_window_info(wid)
                    if window_info:
                        windows.append(window_info)

            return windows

        except subprocess.TimeoutExpired:
            return []

    def get_active_window(self) -> WindowInfo | None:
        """Get the currently active window.

        Returns:
            WindowInfo of the active window, or None.
        """
        if not self._xdotool_available:
            return None

        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                window_id = result.stdout.strip()
                return self._get_window_info(window_id)

        except subprocess.TimeoutExpired:
            pass

        return None

    def minimize_window(self, window_id: str) -> dict[str, Any]:
        """Minimize a window.

        Args:
            window_id: Window ID to minimize.

        Returns:
            Result dict with status.
        """
        if not self._xdotool_available:
            return {"status": "error", "message": "xdotool not available"}

        try:
            subprocess.run(
                ["xdotool", "windowminimize", "--window", window_id],
                capture_output=True,
                timeout=10,
                check=True,
            )

            return {
                "action": "minimize_window",
                "window_id": window_id,
                "status": "success",
            }

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return {
                "action": "minimize_window",
                "window_id": window_id,
                "status": "error",
                "message": str(e),
            }
