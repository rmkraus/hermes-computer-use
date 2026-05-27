"""Tests for window management functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hermes_computer_use.tools.window import WindowInfo, WindowManager


class TestWindowManager:
    """Tests for the WindowManager class."""

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_check_xdotool_available(self, mock_run):
        """Test xdotool availability detection."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wm = WindowManager()
        assert wm._xdotool_available is True

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_check_xdotool_unavailable(self, mock_run):
        """Test xdotool unavailable detection."""
        mock_run.side_effect = FileNotFoundError("xdotool not found")

        wm = WindowManager()
        assert wm._xdotool_available is False

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_list_windows_no_windows(self, mock_run):
        """Test listing windows when no windows match."""
        mock_result = MagicMock()
        mock_result.returncode = 1  # No matches from xdotool
        mock_run.return_value = mock_result

        wm = WindowManager()
        windows = wm.list_windows()
        assert windows == []

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_focus_window_unavailable(self, mock_run):
        """Test focus window when xdotool not available."""
        mock_run.side_effect = FileNotFoundError()

        wm = WindowManager()
        result = wm.focus_window("12345")

        assert result["status"] == "error"
        assert "xdotool not available" in result["message"]

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_search_windows_unavailable(self, mock_run):
        """Test search windows when xdotool not available."""
        mock_run.side_effect = FileNotFoundError()

        wm = WindowManager()
        windows = wm.search_windows("firefox")
        assert windows == []

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_get_active_window_unavailable(self, mock_run):
        """Test getting active window when xdotool not available."""
        mock_run.side_effect = FileNotFoundError()

        wm = WindowManager()
        window = wm.get_active_window()
        assert window is None

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_minimize_window_unavailable(self, mock_run):
        """Test minimize window when xdotool not available."""
        mock_run.side_effect = FileNotFoundError()

        wm = WindowManager()
        result = wm.minimize_window("12345")

        assert result["status"] == "error"

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_minimize_window_error(self, mock_run):
        """Test minimize window on subprocess error."""
        import subprocess as sp

        mock_run.side_effect = sp.CalledProcessError(1, "xdotool")

        wm = WindowManager()
        result = wm.minimize_window("99999")

        assert result["status"] == "error"


class TestWindowInfo:
    """Tests for WindowInfo dataclass."""

    def test_window_creation(self):
        """Test creating WindowInfo."""
        w = WindowInfo(
            window_id="12345",
            title="Firefox",
            class_name="firefox",
            pid=1234,
            x=0,
            y=0,
            width=1920,
            height=1080,
        )
        assert w.window_id == "12345"
        assert w.title == "Firefox"
        assert w.geometry == "1920x1080+0+0"

    def test_window_geometry_format(self):
        """Test geometry formatting."""
        w = WindowInfo(
            window_id="99",
            title="Test",
            class_name="test",
            pid=999,
            x=100,
            y=200,
            width=800,
            height=600,
        )
        assert w.geometry == "800x600+100+200"


class TestWindowManagerEdgeCases:
    """Edge case tests for WindowManager."""

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_timeout_on_list(self, mock_run):
        """Test handling timeout during window listing."""
        import subprocess as sp

        mock_run.side_effect = sp.TimeoutExpired("xdotool", 10)

        wm = WindowManager()
        windows = wm.list_windows()
        assert windows == []

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_empty_window_id(self, mock_run):
        """Test handling empty window IDs."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\n\n\n"  # Empty lines
        mock_run.return_value = mock_result

        wm = WindowManager()
        windows = wm.list_windows()
        assert windows == []

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_search_empty_term(self, mock_run):
        """Test searching with empty term."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        wm = WindowManager()
        windows = wm.search_windows("")
        assert windows == []
