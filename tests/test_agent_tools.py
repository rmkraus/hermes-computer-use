"""Tests for agent/tools.py — LangChain StructuredTool wrappers.

All tests run without a real display or LLM by mocking pyautogui,
screenshot capture, and window manager calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hermes_computer_use.safety.checker import SafetyChecker


@pytest.fixture()
def safety():
    """Fresh SafetyChecker for each test."""
    return SafetyChecker()


@pytest.fixture()
def mock_pag():
    """Mock pyautogui module."""
    return MagicMock()


@pytest.fixture()
def tools(safety):
    """All computer-use tools bound to the test SafetyChecker."""
    from hermes_computer_use.agent.tools import get_computer_use_tools
    return {t.name: t for t in get_computer_use_tools(safety_checker=safety)}


# ---------------------------------------------------------------------------
# Import smoke + factory
# ---------------------------------------------------------------------------


class TestToolsImport:
    def test_import_does_not_require_display(self):
        """tools.py must import without crashing even with no DISPLAY set."""
        import hermes_computer_use.agent.tools  # noqa: F401

    def test_get_computer_use_tools_returns_list(self, safety):
        from hermes_computer_use.agent.tools import get_computer_use_tools
        result = get_computer_use_tools(safety_checker=safety)
        assert isinstance(result, list)
        assert len(result) == 11

    def test_tool_names(self, tools):
        expected = {
            "take_screenshot", "zoom_region", "click", "move_mouse", "scroll",
            "type_text", "key_press", "list_windows", "focus_window",
            "run_command", "get_screen_info",
        }
        assert set(tools.keys()) == expected

    def test_tool_funcs_are_type_hint_introspectable(self, tools):
        """Tool functions must not be functools.partial — LangGraph ToolNode calls
        get_type_hints() on them and partial objects are not introspectable modules."""
        import functools
        import typing
        for name, tool in tools.items():
            func = tool.func
            assert not isinstance(func, functools.partial), (
                f"Tool '{name}' func is a functools.partial — LangGraph ToolNode will crash"
            )
            try:
                typing.get_type_hints(func)
            except TypeError as exc:
                pytest.fail(f"Tool '{name}' func not introspectable by get_type_hints: {exc}")

    def test_each_call_gets_independent_checker(self):
        """Two calls to get_computer_use_tools return independently testable tool sets."""
        from hermes_computer_use.agent.tools import get_computer_use_tools
        s1, s2 = SafetyChecker(), SafetyChecker()
        tools1 = get_computer_use_tools(safety_checker=s1)
        tools2 = get_computer_use_tools(safety_checker=s2)
        assert len(tools1) == len(tools2) == 11


# ---------------------------------------------------------------------------
# take_screenshot
# ---------------------------------------------------------------------------


class TestTakeScreenshot:
    def test_returns_base64_on_success(self, tools):
        from hermes_computer_use.tools.screenshot import Screenshot
        fake_shot = Screenshot(data=b"\x89PNG\r\n", width=100, height=100)
        with patch("hermes_computer_use.agent.tools.capture_screenshot", return_value=fake_shot):
            result = tools["take_screenshot"].invoke({})
        assert result.startswith("data:image/png;base64,")

    def test_returns_error_on_failure(self, tools):
        with patch(
            "hermes_computer_use.agent.tools.capture_screenshot",
            side_effect=RuntimeError("No display"),
        ):
            result = tools["take_screenshot"].invoke({})
        assert "Screenshot failed" in result

    def test_returns_data_uri_prefix(self, tools):
        from hermes_computer_use.tools.screenshot import Screenshot
        fake_shot = Screenshot(data=b"PNG", width=10, height=10)
        with patch("hermes_computer_use.agent.tools.capture_screenshot", return_value=fake_shot):
            result = tools["take_screenshot"].invoke({})
        assert result.startswith("data:image/png;base64,")

    def test_accepts_max_dimension(self, tools):
        from hermes_computer_use.tools.screenshot import Screenshot
        fake_shot = Screenshot(data=b"PNG", width=800, height=600)
        with patch(
            "hermes_computer_use.agent.tools.capture_screenshot", return_value=fake_shot
        ) as mock_cap:
            tools["take_screenshot"].invoke({"max_dimension": 512})
        mock_cap.assert_called_once_with(max_dimension=512)


# ---------------------------------------------------------------------------
# zoom_region
# ---------------------------------------------------------------------------


class TestZoomRegion:
    def test_returns_base64_on_success(self, tools):
        from hermes_computer_use.tools.screenshot import Screenshot
        fake_shot = Screenshot(data=b"\x89PNG", width=200, height=200)
        with patch("hermes_computer_use.agent.tools.zoom_screenshot", return_value=fake_shot):
            result = tools["zoom_region"].invoke({"x": 0, "y": 0, "width": 100, "height": 100})
        assert result.startswith("data:image/png;base64,")

    def test_returns_error_on_failure(self, tools):
        with patch(
            "hermes_computer_use.agent.tools.zoom_screenshot",
            side_effect=ValueError("Region dimensions must be positive"),
        ):
            result = tools["zoom_region"].invoke({"x": 0, "y": 0, "width": 0, "height": 0})
        assert "Zoom failed" in result


# ---------------------------------------------------------------------------
# click
# ---------------------------------------------------------------------------


class TestClick:
    def test_left_click(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["click"].invoke({"x": 100, "y": 200})
        assert "100" in result and "200" in result
        mock_pag.click.assert_called_once_with(100, 200, button="left")

    def test_double_click(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["click"].invoke({"x": 50, "y": 60, "clicks": 2})
        assert "2x" in result
        mock_pag.doubleClick.assert_called_once()

    def test_right_click(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            tools["click"].invoke({"x": 10, "y": 10, "button": "right"})
        mock_pag.click.assert_called_once_with(10, 10, button="right")

    def test_returns_error_on_failure(self, tools):
        bad_pag = MagicMock()
        bad_pag.click.side_effect = Exception("Display error")
        with patch.dict("sys.modules", {"pyautogui": bad_pag}):
            result = tools["click"].invoke({"x": 0, "y": 0})
        assert "Click failed" in result


# ---------------------------------------------------------------------------
# move_mouse
# ---------------------------------------------------------------------------


class TestMoveMouse:
    def test_moves_to_coordinates(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["move_mouse"].invoke({"x": 300, "y": 400})
        assert "300" in result and "400" in result
        mock_pag.moveTo.assert_called_once_with(300, 400, duration=0.1)

    def test_custom_duration(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            tools["move_mouse"].invoke({"x": 0, "y": 0, "duration": 0.5})
        mock_pag.moveTo.assert_called_once_with(0, 0, duration=0.5)


# ---------------------------------------------------------------------------
# scroll
# ---------------------------------------------------------------------------


class TestScroll:
    def test_scroll_up(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["scroll"].invoke({"x": 100, "y": 100, "amount": 3})
        assert "3" in result
        mock_pag.scroll.assert_called_once_with(3, x=100, y=100)

    def test_scroll_down(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["scroll"].invoke({"x": 0, "y": 0, "amount": -5})
        assert "-5" in result


# ---------------------------------------------------------------------------
# type_text
# ---------------------------------------------------------------------------


class TestTypeText:
    def test_normal_text(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["type_text"].invoke({"text": "hello world"})
        assert "11 characters" in result
        mock_pag.write.assert_called_once()

    def test_blocks_dangerous_content(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["type_text"].invoke({"text": "rm -rf /"})
        assert "Blocked" in result
        mock_pag.write.assert_not_called()

    def test_blocks_password_content(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["type_text"].invoke({"text": "password: secret123"})
        assert "Blocked" in result


# ---------------------------------------------------------------------------
# key_press
# ---------------------------------------------------------------------------


class TestKeyPress:
    def test_single_key(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["key_press"].invoke({"keys": "enter"})
        assert "enter" in result
        mock_pag.press.assert_called_once_with("enter")

    def test_hotkey(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["key_press"].invoke({"keys": "ctrl+c"})
        assert "ctrl+c" in result
        mock_pag.hotkey.assert_called_once_with("ctrl", "c")

    def test_blocked_combo(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["key_press"].invoke({"keys": "alt+f4"})
        assert "Blocked" in result

    def test_sequential_keys(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            tools["key_press"].invoke({"keys": "enter,enter"})
        assert mock_pag.press.call_count == 2

    def test_three_key_combo(self, tools, mock_pag):
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = tools["key_press"].invoke({"keys": "ctrl+alt+t"})
        assert "ctrl+alt+t" in result
        mock_pag.hotkey.assert_called_once_with("ctrl", "alt", "t")


# ---------------------------------------------------------------------------
# list_windows
# ---------------------------------------------------------------------------


class TestListWindows:
    def test_no_windows(self, tools):
        with patch("hermes_computer_use.agent.tools.WindowManager") as mock_wm:
            mock_wm.return_value.list_windows.return_value = []
            result = tools["list_windows"].invoke({})
        assert "No windows" in result

    def test_with_windows(self, tools):
        from hermes_computer_use.tools.window import WindowInfo
        win = WindowInfo(
            window_id="12345", title="Firefox", class_name="Firefox",
            pid=1000, x=0, y=0, width=1200, height=800,
        )
        with patch("hermes_computer_use.agent.tools.WindowManager") as mock_wm:
            mock_wm.return_value.list_windows.return_value = [win]
            result = tools["list_windows"].invoke({})
        assert "12345" in result
        assert "Firefox" in result
        assert "1200x800" in result


# ---------------------------------------------------------------------------
# focus_window
# ---------------------------------------------------------------------------


class TestFocusWindow:
    def test_success(self, tools):
        with patch("hermes_computer_use.agent.tools.WindowManager") as mock_wm:
            mock_wm.return_value.focus_window.return_value = {"status": "success"}
            result = tools["focus_window"].invoke({"window_id": "99"})
        assert "99" in result

    def test_failure(self, tools):
        with patch("hermes_computer_use.agent.tools.WindowManager") as mock_wm:
            mock_wm.return_value.focus_window.return_value = {
                "status": "error", "message": "Window not found"
            }
            result = tools["focus_window"].invoke({"window_id": "0"})
        assert "failed" in result


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_safe_command(self, tools):
        result = tools["run_command"].invoke({"command": "echo hello"})
        assert "hello" in result

    def test_blocked_dangerous_command(self, tools):
        result = tools["run_command"].invoke({"command": "rm -rf /tmp/test"})
        assert "blocked" in result.lower()

    def test_command_timeout(self, tools):
        result = tools["run_command"].invoke({"command": "sleep 60", "timeout": 1})
        assert "timed out" in result.lower()

    def test_command_with_output(self, tools):
        result = tools["run_command"].invoke({"command": "echo 'test output'"})
        assert "test output" in result

    def test_nonzero_exit_code_shown(self, tools):
        result = tools["run_command"].invoke({"command": "exit 42"})
        assert "42" in result


# ---------------------------------------------------------------------------
# get_screen_info
# ---------------------------------------------------------------------------


class TestGetScreenInfo:
    def test_no_display(self, tools):
        fake_info = {"server_type": "none", "display": ""}
        with patch("hermes_computer_use.agent.tools.get_display_info", return_value=fake_info):
            result = tools["get_screen_info"].invoke({})
        assert "server_type=none" in result

    def test_with_x11_display(self, tools):
        from hermes_computer_use.tools.screenshot import Screenshot
        fake_info = {"server_type": "x11", "display": ":0"}
        fake_shot = Screenshot(data=b"PNG", width=1920, height=1080)
        with (
            patch("hermes_computer_use.agent.tools.get_display_info", return_value=fake_info),
            patch("hermes_computer_use.agent.tools.capture_screenshot", return_value=fake_shot),
        ):
            result = tools["get_screen_info"].invoke({})
        assert "width=1920" in result
        assert "height=1080" in result
        assert "x11" in result
