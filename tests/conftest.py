"""Shared test fixtures and configuration."""

from __future__ import annotations

import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def mock_pyautogui():
    """Automatically mock pyautogui for all tests to prevent display errors.

    Yields the mock as 'mock_pag' so tests that need it can request it by
    either the fixture name 'mock_pyautogui' or the alias 'mock_pag'.
    """
    with patch("hermes_computer_use.tools.input.pyautogui") as mock_pag:
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.1
        mock_pag.size.return_value = (1920, 1080)
        yield mock_pag


# Alias so tests can request either name
@pytest.fixture
def mock_pag(mock_pyautogui):
    """Alias for mock_pyautogui — yields the same mock object."""
    return mock_pyautogui


@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables to prevent display and API key errors."""
    with patch.dict(os.environ, {"DISPLAY": ":0"}):
        yield


@pytest.fixture
def sample_screenshot() -> bytes:
    """Generate a small sample PNG image for testing."""
    img = Image.new("RGB", (1920, 1080), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def small_screenshot() -> bytes:
    """Generate a smaller PNG for faster tests."""
    img = Image.new("RGB", (640, 480), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def mock_input_simulator():
    """Create a mocked InputSimulator for testing."""
    with patch("hermes_computer_use.tools.input.InputSimulator") as mock_simulator:
        mock = MagicMock()
        mock.click.return_value = {"action": "click", "status": "success"}
        mock.move.return_value = {"action": "move", "status": "success"}
        mock.scroll.return_value = {"action": "scroll", "status": "success"}
        mock.type_text.return_value = {"action": "type", "status": "success"}
        mock.key_combo.return_value = {"action": "key_combo", "status": "success"}
        mock.press_key.return_value = {"action": "press_key", "status": "success"}
        mock.pag = MagicMock()
        mock.pag.size.return_value = (1920, 1080)
        mock.pag.FAILSAFE = True
        mock.pag.PAUSE = 0.1
        mock_simulator.return_value = mock
        yield mock


@pytest.fixture
def mock_safety_checker():
    """Create a mocked SafetyChecker for testing."""
    with patch("hermes_computer_use.safety.checker.SafetyChecker") as mock_checker:
        mock = MagicMock()
        mock.check_all.return_value = MagicMock(safe=True, reason=None)
        mock.check_text.return_value = MagicMock(safe=True, reason=None)
        mock.check_key_combo.return_value = MagicMock(safe=True, reason=None)
        mock.check_coordinate.return_value = MagicMock(safe=True, reason=None)
        mock.check_rate_limit.return_value = MagicMock(safe=True, reason=None)
        mock.record_action.return_value = None
        mock_checker.return_value = mock
        yield mock


@pytest.fixture
def mock_display_env():
    """Mock environment variables for display server testing."""
    with patch.dict("os.environ", {"DISPLAY": ":0"}):
        yield


@pytest.fixture
def mock_xdotool():
    """Mock xdotool subprocess calls."""
    with patch("hermes_computer_use.tools.window.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "12345678"
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_capture_screenshot():
    """Mock capture_screenshot function."""
    from hermes_computer_use.tools.screenshot import Screenshot

    with patch(
        "hermes_computer_use.tools.screenshot.capture_screenshot"
    ) as mock:
        mock.return_value = Screenshot(
            data=b"fake_png_data",
            width=1920,
            height=1080,
        )
        yield mock


@pytest.fixture
def test_data_dir() -> Path:
    """Path to test data directory."""
    return Path(__file__).parent / "data"
