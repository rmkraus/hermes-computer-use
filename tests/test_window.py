"""Tests for window management functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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


class TestGetWindowInfo:
    """Tests for WindowManager._get_window_info."""

    def _make_run(self, title="Firefox", class_name="firefox", pid="1234",
                  geometry="X=10\nY=20\nWIDTH=800\nHEIGHT=600"):
        """Return a side_effect function that sequences xdotool responses."""

        responses = [title, class_name, pid, geometry]
        call_count = [0]

        def fake_run(cmd, **kwargs):
            # First call is __init__ xdotool --version check
            if "--version" in cmd:
                r = MagicMock()
                r.returncode = 0
                return r
            idx = call_count[0] % len(responses)
            call_count[0] += 1
            r = MagicMock()
            r.returncode = 0
            r.stdout = responses[idx]
            return r

        return fake_run

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_returns_window_info(self, mock_run):
        """_get_window_info parses xdotool output into a WindowInfo."""
        responses = iter([
            MagicMock(returncode=0, stdout=""),          # --version check
            MagicMock(returncode=0, stdout="Firefox"),   # getwindowname
            MagicMock(returncode=0, stdout="firefox"),   # getwindowclass
            MagicMock(returncode=0, stdout="1234"),      # getwindowpid
            MagicMock(returncode=0, stdout="X=10\nY=20\nWIDTH=800\nHEIGHT=600"),  # getwindowgeometry
        ])
        mock_run.side_effect = lambda *a, **k: next(responses)

        wm = WindowManager()
        info = wm._get_window_info("99999")

        assert info is not None
        assert info.title == "Firefox"
        assert info.class_name == "firefox"
        assert info.pid == 1234
        assert info.x == 10
        assert info.y == 20
        assert info.width == 800
        assert info.height == 600

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_returns_none_on_timeout(self, mock_run):
        """_get_window_info returns None on TimeoutExpired."""
        import subprocess as sp

        call_count = [0]

        def fake_run(cmd, **kwargs):
            if "--version" in cmd:
                r = MagicMock()
                r.returncode = 0
                return r
            call_count[0] += 1
            if call_count[0] >= 1:
                raise sp.TimeoutExpired("xdotool", 5)
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = fake_run
        wm = WindowManager()
        result = wm._get_window_info("12345")
        assert result is None

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_handles_missing_geometry_fields(self, mock_run):
        """_get_window_info gracefully handles partial geometry output."""
        responses = iter([
            MagicMock(returncode=0, stdout=""),       # --version
            MagicMock(returncode=0, stdout="App"),    # name
            MagicMock(returncode=0, stdout="app"),    # class
            MagicMock(returncode=0, stdout="42"),     # pid
            MagicMock(returncode=0, stdout=""),       # geometry — empty
        ])
        mock_run.side_effect = lambda *a, **k: next(responses)

        wm = WindowManager()
        info = wm._get_window_info("77777")

        assert info is not None
        assert info.x == 0
        assert info.y == 0
        assert info.width == 0
        assert info.height == 0


class TestFocusWindow:
    """Tests for WindowManager.focus_window."""

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_success(self, mock_run):
        """focus_window returns success dict on happy path."""
        responses = iter([
            MagicMock(returncode=0, stdout=""),  # --version
            MagicMock(returncode=0),             # windowfocus
        ])
        mock_run.side_effect = lambda *a, **k: next(responses)

        wm = WindowManager()
        result = wm.focus_window("12345")

        assert result["status"] == "success"
        assert result["window_id"] == "12345"

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_called_process_error(self, mock_run):
        """focus_window returns error dict on CalledProcessError."""
        import subprocess as sp

        responses = iter([
            MagicMock(returncode=0, stdout=""),                    # --version
            sp.CalledProcessError(1, "xdotool"),                   # windowfocus fails
        ])
        mock_run.side_effect = lambda *a, **k: (
            next(responses) if not isinstance(
                (v := responses.__next__ if False else None), Exception
            ) else (_ for _ in ()).throw(next(responses))
        )
        # Simpler approach: use side_effect list
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            sp.CalledProcessError(1, "xdotool"),
        ]

        wm = WindowManager()
        result = wm.focus_window("12345")
        assert result["status"] == "error"
        assert "Failed to focus" in result["message"]

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_timeout(self, mock_run):
        """focus_window returns error dict on TimeoutExpired."""
        import subprocess as sp

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            sp.TimeoutExpired("xdotool", 10),
        ]

        wm = WindowManager()
        result = wm.focus_window("12345")
        assert result["status"] == "error"
        assert "timed out" in result["message"]


class TestSearchWindows:
    """Tests for WindowManager.search_windows."""

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_returns_matching_windows(self, mock_run):
        """search_windows returns populated list when xdotool finds matches."""
        responses = [
            MagicMock(returncode=0, stdout=""),              # --version
            MagicMock(returncode=0, stdout="11111\n22222"),  # search --name
            # _get_window_info for 11111: name, class, pid, geometry
            MagicMock(returncode=0, stdout="Firefox"),
            MagicMock(returncode=0, stdout="firefox"),
            MagicMock(returncode=0, stdout="100"),
            MagicMock(returncode=0, stdout="X=0\nY=0\nWIDTH=1920\nHEIGHT=1080"),
            # _get_window_info for 22222
            MagicMock(returncode=0, stdout="Terminal"),
            MagicMock(returncode=0, stdout="gnome-terminal"),
            MagicMock(returncode=0, stdout="200"),
            MagicMock(returncode=0, stdout="X=0\nY=0\nWIDTH=800\nHEIGHT=600"),
        ]
        mock_run.side_effect = responses

        wm = WindowManager()
        windows = wm.search_windows("fire")

        assert len(windows) == 2
        assert windows[0].title == "Firefox"
        assert windows[1].title == "Terminal"

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_timeout_returns_empty(self, mock_run):
        """search_windows returns [] on TimeoutExpired."""
        import subprocess as sp

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            sp.TimeoutExpired("xdotool", 10),
        ]

        wm = WindowManager()
        result = wm.search_windows("anything")
        assert result == []

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_skips_windows_where_info_is_none(self, mock_run):
        """search_windows skips windows for which _get_window_info returns None."""
        import subprocess as sp

        call_count = [0]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="")
            if "search" in cmd and "--name" in cmd:
                return MagicMock(returncode=0, stdout="55555")
            raise sp.TimeoutExpired("xdotool", 5)

        mock_run.side_effect = fake_run
        wm = WindowManager()
        assert wm.search_windows("test") == []


class TestGetActiveWindow:
    """Tests for WindowManager.get_active_window."""

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_returns_active_window(self, mock_run):
        """get_active_window returns WindowInfo for the focused window."""
        responses = [
            MagicMock(returncode=0, stdout=""),          # --version
            MagicMock(returncode=0, stdout="55555"),     # getactivewindow
            MagicMock(returncode=0, stdout="Code"),      # name
            MagicMock(returncode=0, stdout="code"),      # class
            MagicMock(returncode=0, stdout="9999"),      # pid
            MagicMock(returncode=0, stdout="X=0\nY=0\nWIDTH=1280\nHEIGHT=720"),
        ]
        mock_run.side_effect = responses

        wm = WindowManager()
        result = wm.get_active_window()

        assert result is not None
        assert result.title == "Code"
        assert result.width == 1280

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_returns_none_when_getactivewindow_fails(self, mock_run):
        """get_active_window returns None when xdotool returns non-zero."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),   # --version
            MagicMock(returncode=1, stdout=""),   # getactivewindow fails
        ]

        wm = WindowManager()
        result = wm.get_active_window()
        assert result is None

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        """get_active_window returns None on TimeoutExpired."""
        import subprocess as sp

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            sp.TimeoutExpired("xdotool", 5),
        ]

        wm = WindowManager()
        result = wm.get_active_window()
        assert result is None


class TestMinimizeWindow:
    """Tests for WindowManager.minimize_window."""

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_success(self, mock_run):
        """minimize_window returns success on happy path."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # --version
            MagicMock(returncode=0),             # windowminimize
        ]

        wm = WindowManager()
        result = wm.minimize_window("12345")

        assert result["status"] == "success"
        assert result["window_id"] == "12345"

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_timeout(self, mock_run):
        """minimize_window returns error on TimeoutExpired."""
        import subprocess as sp

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            sp.TimeoutExpired("xdotool", 10),
        ]

        wm = WindowManager()
        result = wm.minimize_window("12345")
        assert result["status"] == "error"


class TestListWindows:
    """Tests for WindowManager.list_windows with full _get_window_info integration."""

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_list_returns_windows(self, mock_run):
        """list_windows returns populated list when xdotool succeeds."""
        responses = [
            MagicMock(returncode=0, stdout=""),              # --version
            MagicMock(returncode=0, stdout="33333"),         # search --onlyvisible
            MagicMock(returncode=0, stdout="Nautilus"),      # name
            MagicMock(returncode=0, stdout="nautilus"),      # class
            MagicMock(returncode=0, stdout="500"),           # pid
            MagicMock(returncode=0, stdout="X=0\nY=0\nWIDTH=640\nHEIGHT=480"),
        ]
        mock_run.side_effect = responses

        wm = WindowManager()
        windows = wm.list_windows()

        assert len(windows) == 1
        assert windows[0].title == "Nautilus"

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_list_returns_empty_when_search_fails(self, mock_run):
        """list_windows returns [] when xdotool search returns non-zero."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),   # --version
            MagicMock(returncode=1, stdout=""),   # search fails
        ]
        wm = WindowManager()
        assert wm.list_windows() == []

    @patch("hermes_computer_use.tools.window.subprocess.run")
    def test_list_skips_windows_with_no_info(self, mock_run):
        """list_windows skips window IDs for which _get_window_info returns None."""
        import subprocess as sp

        call_count = [0]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="")
            if "search" in cmd:
                return MagicMock(returncode=0, stdout="44444")
            # _get_window_info: first sub-call raises TimeoutExpired → returns None
            raise sp.TimeoutExpired("xdotool", 5)

        mock_run.side_effect = fake_run
        wm = WindowManager()
        windows = wm.list_windows()
        assert windows == []
