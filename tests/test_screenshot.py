"""Tests for screenshot capture functionality."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from PIL import Image

from hermes_computer_use.tools.screenshot import Screenshot, capture_screenshot, get_display_info


class TestScreenshot:
    """Tests for the Screenshot dataclass."""

    def test_screenshot_creation(self, sample_screenshot):
        """Test creating a Screenshot with valid data."""
        ss = Screenshot(
            data=sample_screenshot,
            width=1920,
            height=1080,
        )
        assert ss.width == 1920
        assert ss.height == 1080
        assert ss.scale_factor == 1.0
        assert len(ss.data) > 0
        assert ss.data == sample_screenshot

    def test_to_base64(self, sample_screenshot):
        """Test base64 encoding."""
        ss = Screenshot(data=sample_screenshot, width=100, height=100)
        b64 = ss.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 0
        # Should be valid base64
        import base64
        decoded = base64.b64decode(b64)
        assert decoded == sample_screenshot

    def test_to_urn(self, sample_screenshot):
        """Test data URI creation."""
        ss = Screenshot(data=sample_screenshot, width=100, height=100)
        urn = ss.to_urn()
        assert urn.startswith("data:image/png;base64,")
        assert len(urn) > 50

    def test_resize_smaller(self, sample_screenshot):
        """Test resize when image is already small."""
        ss = Screenshot(data=sample_screenshot, width=100, height=100)
        resized = ss.resize(max_dimension=512)
        # Should not resize since already small
        assert resized.width == 100
        assert resized.height == 100

    def test_resize_larger(self):
        """Test resize when image exceeds max dimension."""
        img = Image.new("RGB", (2048, 1536), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        data = buf.read()

        ss = Screenshot(data=data, width=2048, height=1536)
        resized = ss.resize(max_dimension=1024)

        assert resized.width <= 1024
        assert resized.height <= 1024
        assert resized.width > 0
        assert resized.height > 0
        assert len(resized.data) > 0

    def test_resize_with_scale_factor(self, sample_screenshot):
        """Test that resize calculates scale factor correctly."""
        ss = Screenshot(data=sample_screenshot, width=100, height=100)
        resized = ss.resize(max_dimension=50)
        assert resized.scale_factor == pytest.approx(0.5, abs=0.01)


class TestDisplayInfo:
    """Tests for display information detection."""

    def test_no_display(self, monkeypatch):
        """Test when no display is set — server_type should be 'none'."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        info = get_display_info()
        # display falls back to "" when DISPLAY is unset (not ":0")
        assert info["server_type"] == "none"

    def test_x11_display(self, monkeypatch):
        """Test X11 display detection."""
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        info = get_display_info()
        assert info["display"] == ":0"
        assert info["server_type"] == "x11"

    def test_wayland_display(self, monkeypatch):
        """Test Wayland display detection."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")

        info = get_display_info()
        assert info["wayland"] is True
        assert info["server_type"] == "wayland"


class TestCaptureScreenshot:
    """Tests for screenshot capture."""

    def test_no_display_error(self, monkeypatch):
        """Test error when no display server is available."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        with pytest.raises(RuntimeError, match="No display server"):
            capture_screenshot()

    def test_returns_screenshot_object(self, sample_screenshot):
        """Test that capture_screenshot returns a Screenshot when mocked."""
        expected = Screenshot(data=sample_screenshot, width=1920, height=1080)

        with patch(
            "hermes_computer_use.tools.screenshot.capture_screenshot",
            return_value=expected,
        ) as mock_cap:
            result = mock_cap()
            assert isinstance(result, Screenshot)
            assert result.width == 1920
            assert result.height == 1080

    def test_pyautogui_fallback(self, sample_screenshot):
        """Test PyAutoGUI fallback — _capture_pyautogui must return a Screenshot."""
        scrot_ss = Screenshot(data=sample_screenshot, width=1920, height=1080)

        with patch("hermes_computer_use.tools.screenshot._capture_scrot", return_value=None):
            with patch("hermes_computer_use.tools.screenshot._capture_xdotool", return_value=None):
                with patch(
                    "hermes_computer_use.tools.screenshot._capture_pyautogui",
                    return_value=scrot_ss,
                ):
                    ss = capture_screenshot(max_dimension=4096)  # No resize
                    assert ss.width == 1920
                    assert ss.height == 1080

    def test_resize_on_capture(self):
        """Test that screenshots are auto-resized when they exceed max_dimension."""
        big_img = Image.new("RGB", (4000, 3000), color="red")
        buf = io.BytesIO()
        big_img.save(buf, format="PNG")
        buf.seek(0)
        big_data = buf.read()
        big_ss = Screenshot(data=big_data, width=4000, height=3000)

        with patch("hermes_computer_use.tools.screenshot._capture_scrot", return_value=None):
            with patch("hermes_computer_use.tools.screenshot._capture_xdotool", return_value=None):
                with patch(
                    "hermes_computer_use.tools.screenshot._capture_pyautogui",
                    return_value=big_ss,
                ):
                    ss = capture_screenshot(max_dimension=1024)
                    assert ss.width <= 1024
                    assert ss.height <= 1024

    def test_region_capture(self):
        """Test screenshot capture with a region parameter."""
        # Build a screenshot sized to match what a region capture would return
        region_img = Image.new("RGB", (400, 300), color="blue")
        buf = io.BytesIO()
        region_img.save(buf, format="PNG")
        buf.seek(0)
        region_data = buf.read()
        region_ss = Screenshot(data=region_data, width=400, height=300)

        with patch("hermes_computer_use.tools.screenshot._capture_scrot", return_value=None):
            with patch("hermes_computer_use.tools.screenshot._capture_xdotool", return_value=None):
                with patch(
                    "hermes_computer_use.tools.screenshot._capture_pyautogui",
                    return_value=region_ss,
                ):
                    ss = capture_screenshot(region=(100, 100, 400, 300), max_dimension=4096)
                    assert ss.width == 400
                    assert ss.height == 300

    def test_scrot_preferred_over_fallbacks(self, sample_screenshot):
        """Test that scrot is used when available (first in preference order)."""
        scrot_ss = Screenshot(data=sample_screenshot, width=1920, height=1080)

        with patch(
            "hermes_computer_use.tools.screenshot._capture_scrot",
            return_value=scrot_ss,
        ) as mock_scrot:
            with patch(
                "hermes_computer_use.tools.screenshot._capture_xdotool",
                return_value=None,
            ) as mock_xd:
                with patch(
                    "hermes_computer_use.tools.screenshot._capture_pyautogui",
                    return_value=None,
                ) as mock_pag:
                    ss = capture_screenshot(max_dimension=4096)
                    assert ss.width == 1920
                    assert mock_scrot.called
                    assert not mock_xd.called
                    assert not mock_pag.called
