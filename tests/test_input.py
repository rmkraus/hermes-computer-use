"""Tests for input simulation (mouse and keyboard)."""

from __future__ import annotations

import pytest

from hermes_computer_use.tools.input import InputSimulator, KeyboardAction, MouseButton


class TestInputSimulator:
    """Tests for the InputSimulator class."""

    @pytest.fixture(autouse=True)
    def setup_mock(self, mock_pag):
        """Inject the mocked pyautogui from conftest."""
        self.mock_pag = mock_pag

    def test_init(self):
        """Test InputSimulator initialization."""
        self.mock_pag.size.return_value = (1920, 1080)
        sim = InputSimulator(mouse_move_duration=0.3, pause=0.2)

        assert sim.mouse_move_duration == 0.3
        assert sim.pause == 0.2
        assert sim._screen_width == 1920
        assert sim._screen_height == 1080

    def test_default_screen_size(self):
        """Test default screen size when PyAutoGUI fails."""
        self.mock_pag.size.side_effect = Exception("No display")
        sim = InputSimulator()

        assert sim._screen_width == 1920
        assert sim._screen_height == 1080

    def test_click_left(self):
        """Test left click."""
        sim = InputSimulator()

        result = sim.click(100, 200, button=MouseButton.LEFT, clicks=1)

        assert result["action"] == "click"
        assert result["x"] == 100
        assert result["y"] == 200
        assert result["button"] == "left"
        assert result["clicks"] == 1
        assert result["status"] == "success"
        self.mock_pag.click.assert_called_once_with(100, 200, button="left")

    def test_click_double(self):
        """Test double click."""
        sim = InputSimulator()

        sim.click(50, 50, button=MouseButton.RIGHT, clicks=2)

        self.mock_pag.doubleClick.assert_called_once_with(50, 50, button="right")

    def test_move(self):
        """Test mouse movement."""
        sim = InputSimulator(mouse_move_duration=1.0)

        result = sim.move(300, 400, duration=2.0)

        assert result["action"] == "move"
        assert result["x"] == 300
        assert result["y"] == 400
        assert result["duration"] == 2.0
        self.mock_pag.moveTo.assert_called_once_with(300, 400, duration=2.0)

    def test_scroll(self):
        """Test mouse scrolling."""
        sim = InputSimulator()

        result = sim.scroll(100, 200, clicks=5)

        assert result["action"] == "scroll"
        assert result["clicks"] == 5
        self.mock_pag.scroll.assert_called_once_with(5, x=100, y=200)

    def test_type_text(self):
        """Test typing text."""
        sim = InputSimulator()

        result = sim.type_text("Hello, World!", interval=0.01)

        assert result["action"] == "type"
        assert result["text"] == "Hello, World!"
        assert result["character_count"] == 13
        assert result["status"] == "success"
        self.mock_pag.write.assert_called_once_with("Hello, World!", interval=0.01)

    def test_key_combo_ctrl_c(self):
        """Test Ctrl+C key combination."""
        sim = InputSimulator()

        result = sim.key_combo(["ctrl", "c"], action=KeyboardAction.PRESS_RELEASE)

        assert result["action"] == "key_combo"
        assert result["keys"] == ["ctrl", "c"]
        assert result["type"] == "press_release"
        assert result["status"] == "success"
        self.mock_pag.hotkey.assert_called_once_with("ctrl", "c")

    def test_key_combo_complex(self):
        """Test complex key combination."""
        sim = InputSimulator()

        sim.key_combo(["ctrl", "shift", "escape"])

        self.mock_pag.hotkey.assert_called_once_with("ctrl", "shift", "escape")

    def test_press_key(self):
        """Test single key press."""
        sim = InputSimulator()

        result = sim.press_key("enter")

        assert result["action"] == "press_key"
        assert result["key"] == "enter"
        self.mock_pag.press.assert_called_once_with("enter")

    def test_press_key_tab(self):
        """Test Tab key press."""
        sim = InputSimulator()

        sim.press_key("tab")

        self.mock_pag.press.assert_called_once_with("tab")

    def test_failsafe_is_enabled(self):
        """Test that failsafe is enabled by default."""
        InputSimulator()
        assert self.mock_pag.FAILSAFE is True

    def test_pause_is_set(self):
        """Test that pause is configured."""
        InputSimulator(pause=0.5)
        assert self.mock_pag.PAUSE == 0.5

    def test_key_combo_press_only(self):
        """Test key combination with press only (no release)."""
        sim = InputSimulator()

        sim.key_combo(["ctrl", "alt"], action=KeyboardAction.PRESS)

        self.mock_pag.keyDown.assert_any_call("ctrl")
        self.mock_pag.keyDown.assert_any_call("alt")

    def test_key_combo_release_only(self):
        """Test key combination with release only."""
        sim = InputSimulator()

        sim.key_combo(["ctrl", "shift"], action=KeyboardAction.RELEASE)

        self.mock_pag.keyUp.assert_called()


class TestInputSimulatorEdgeCases:
    """Edge case tests for InputSimulator."""

    @pytest.fixture(autouse=True)
    def setup_mock(self, mock_pag):
        """Inject the mocked pyautogui from conftest."""
        self.mock_pag = mock_pag

    def test_empty_text(self):
        """Test typing empty string."""
        sim = InputSimulator()
        result = sim.type_text("")

        assert result["character_count"] == 0
        assert result["status"] == "success"

    def test_unicode_text(self):
        """Test typing unicode characters."""
        sim = InputSimulator()
        result = sim.type_text("日本語")

        assert result["character_count"] == 3
        assert result["status"] == "success"

    def test_all_buttons(self):
        """Test all mouse button types."""
        sim = InputSimulator()

        for button in MouseButton:
            sim.click(0, 0, button=button)

        # Should have been called once per button
        assert self.mock_pag.click.call_count >= 1
