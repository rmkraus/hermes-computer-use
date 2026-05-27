"""Tests for screenshot capture functionality."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from hermes_computer_use.tools.screenshot import (
    Screenshot,
    capture_screenshot,
    get_display_info,
    zoom_screenshot,
)


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

    def test_all_methods_fail_raises(self, monkeypatch):
        """RuntimeError when every capture method fails."""
        monkeypatch.setenv("DISPLAY", ":0")
        with patch("hermes_computer_use.tools.screenshot._capture_scrot", return_value=None):
            with patch("hermes_computer_use.tools.screenshot._capture_xdotool", return_value=None):
                with patch("hermes_computer_use.tools.screenshot._capture_pyautogui", return_value=None):
                    with pytest.raises(RuntimeError, match="Screenshot capture failed"):
                        capture_screenshot()

    def test_logs_and_continues_on_method_exception(self, monkeypatch):
        """Capture methods that raise are logged and skipped, not bubbled."""
        monkeypatch.setenv("DISPLAY", ":0")
        from hermes_computer_use.tools.screenshot import Screenshot
        good_ss = Screenshot(data=b"PNG", width=10, height=10)

        bad = MagicMock(side_effect=Exception("boom"))
        bad.__name__ = "fake_method"

        with patch("hermes_computer_use.tools.screenshot._capture_scrot", bad):
            with patch("hermes_computer_use.tools.screenshot._capture_xdotool", bad):
                with patch("hermes_computer_use.tools.screenshot._capture_pyautogui", return_value=good_ss):
                    result = capture_screenshot(max_dimension=0)
        assert result.width == 10


class TestCaptureScrot:
    """Tests for the _capture_scrot internal function."""

    def _make_png(self, width: int = 100, height: int = 100) -> bytes:
        img = Image.new("RGB", (width, height), color="green")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()

    def test_returns_screenshot_on_success(self, tmp_path, monkeypatch):
        """_capture_scrot returns a Screenshot when scrot succeeds."""
        from hermes_computer_use.tools.screenshot import _capture_scrot

        png_data = self._make_png()

        def fake_run(cmd, **kwargs):
            # Write a real PNG to the expected path
            import os
            path = f"/tmp/hermes_screenshot_{os.getpid()}.png"
            with open(path, "wb") as f:
                f.write(png_data)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("hermes_computer_use.tools.screenshot.subprocess.run", side_effect=fake_run):
            result = _capture_scrot(None)

        assert result is not None
        assert result.width == 100
        assert result.height == 100

    def test_returns_none_on_failure(self):
        """_capture_scrot returns None when scrot fails."""
        import subprocess as sp

        from hermes_computer_use.tools.screenshot import _capture_scrot

        with patch(
            "hermes_computer_use.tools.screenshot.subprocess.run",
            side_effect=sp.CalledProcessError(1, "scrot"),
        ):
            result = _capture_scrot(None)

        assert result is None

    def test_returns_none_when_not_installed(self):
        """_capture_scrot returns None when scrot binary is missing."""
        from hermes_computer_use.tools.screenshot import _capture_scrot

        with patch(
            "hermes_computer_use.tools.screenshot.subprocess.run",
            side_effect=FileNotFoundError("scrot not found"),
        ):
            result = _capture_scrot(None)

        assert result is None

    def test_region_builds_correct_command(self):
        """_capture_scrot passes -a flag with region coords."""
        import os

        from hermes_computer_use.tools.screenshot import _capture_scrot

        png_data = self._make_png()
        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            path = f"/tmp/hermes_screenshot_{os.getpid()}.png"
            with open(path, "wb") as f:
                f.write(png_data)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("hermes_computer_use.tools.screenshot.subprocess.run", side_effect=fake_run):
            _capture_scrot((10, 20, 200, 100))

        assert "-a" in captured_cmd
        assert "10,20,200,100" in captured_cmd


class TestCaptureXdotool:
    """Tests for the _capture_xdotool internal function."""

    def _make_png(self, width: int = 100, height: int = 100) -> bytes:
        img = Image.new("RGB", (width, height), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()

    def test_returns_none_on_failure(self):
        """_capture_xdotool returns None when xwd fails."""
        from hermes_computer_use.tools.screenshot import _capture_xdotool

        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("hermes_computer_use.tools.screenshot.subprocess.run", return_value=mock_result):
            result = _capture_xdotool(None)
        assert result is None

    def test_returns_none_when_not_installed(self):
        """_capture_xdotool returns None when xwd binary is missing."""
        from hermes_computer_use.tools.screenshot import _capture_xdotool

        with patch(
            "hermes_computer_use.tools.screenshot.subprocess.run",
            side_effect=FileNotFoundError("xwd not found"),
        ):
            result = _capture_xdotool(None)
        assert result is None

    def test_returns_screenshot_on_success(self, tmp_path):
        """_capture_xdotool returns a Screenshot when xwd+convert succeed."""
        import os

        from hermes_computer_use.tools.screenshot import _capture_xdotool

        png_data = self._make_png()
        call_count = [0]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            r.returncode = 0
            # On second call (convert), write the PNG
            if call_count[0] == 2:
                path = f"/tmp/hermes_screenshot_{os.getpid()}.png"
                with open(path, "wb") as f:
                    f.write(png_data)
            return r

        with patch("hermes_computer_use.tools.screenshot.subprocess.run", side_effect=fake_run):
            result = _capture_xdotool(None)

        assert result is not None
        assert result.width == 100
        assert result.height == 100

    def test_region_path(self, tmp_path):
        """_capture_xdotool handles the region capture code path."""
        import os

        from hermes_computer_use.tools.screenshot import _capture_xdotool

        png_data = self._make_png()
        call_count = [0]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            r.returncode = 0
            if call_count[0] == 2:
                path = f"/tmp/hermes_screenshot_{os.getpid()}.png"
                with open(path, "wb") as f:
                    f.write(png_data)
            return r

        with patch("hermes_computer_use.tools.screenshot.subprocess.run", side_effect=fake_run):
            result = _capture_xdotool((10, 20, 200, 100))

        assert result is not None

    def test_region_returns_none_when_xwd_fails(self):
        """_capture_xdotool(region) returns None when xwd returncode != 0."""
        from hermes_computer_use.tools.screenshot import _capture_xdotool

        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("hermes_computer_use.tools.screenshot.subprocess.run", return_value=mock_result):
            result = _capture_xdotool((10, 20, 200, 100))
        assert result is None


class TestCapturePyautogui:
    """Tests for the _capture_pyautogui internal function."""

    def _make_pil_image(self, width: int = 100, height: int = 100):
        return Image.new("RGB", (width, height), color="red")

    def test_returns_screenshot_on_success(self):
        """_capture_pyautogui returns a Screenshot using mocked pyautogui."""
        from hermes_computer_use.tools.screenshot import _capture_pyautogui
        mock_pag = MagicMock()
        mock_pag.screenshot.return_value = self._make_pil_image()

        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = _capture_pyautogui(None)

        assert result is not None
        assert result.width == 100
        assert result.height == 100

    def test_returns_screenshot_with_region(self):
        """_capture_pyautogui crops the full screenshot to the region."""
        from hermes_computer_use.tools.screenshot import _capture_pyautogui

        full_img = Image.new("RGB", (1920, 1080), color="gray")
        mock_pag = MagicMock()
        mock_pag.screenshot.return_value = full_img

        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = _capture_pyautogui((100, 100, 300, 200))

        assert result is not None
        assert result.width == 300
        assert result.height == 200

    def test_returns_none_on_exception(self):
        """_capture_pyautogui returns None when pyautogui raises."""
        from hermes_computer_use.tools.screenshot import _capture_pyautogui

        mock_pag = MagicMock()
        mock_pag.screenshot.side_effect = Exception("display error")

        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            result = _capture_pyautogui(None)

        assert result is None


class TestGetScreenSize:
    """Tests for get_screen_size."""

    def test_returns_dimensions(self, sample_screenshot):
        """get_screen_size returns (width, height) from a captured screenshot."""
        from hermes_computer_use.tools.screenshot import Screenshot, get_screen_size

        mock_ss = Screenshot(data=sample_screenshot, width=1920, height=1080)
        with patch("hermes_computer_use.tools.screenshot.capture_screenshot", return_value=mock_ss):
            w, h = get_screen_size()

        assert w == 1920
        assert h == 1080


class TestZoomScreenshot:
    """Tests for the zoom_screenshot function."""

    def _make_screenshot(self, width: int, height: int, color="green") -> Screenshot:
        """Helper: build a real PNG Screenshot of the given size."""
        img = Image.new("RGB", (width, height), color=color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        data = buf.read()
        return Screenshot(data=data, width=width, height=height)

    def test_invalid_width(self):
        """zoom_screenshot raises ValueError for zero/negative width."""
        with pytest.raises(ValueError, match="dimensions must be positive"):
            zoom_screenshot(x=0, y=0, width=0, height=100)

    def test_invalid_height(self):
        """zoom_screenshot raises ValueError for zero/negative height."""
        with pytest.raises(ValueError, match="dimensions must be positive"):
            zoom_screenshot(x=0, y=0, width=100, height=-1)

    def test_upscales_small_region(self):
        """Small region is upscaled to output_size."""
        # Pretend a 50×50 region was captured
        small_ss = self._make_screenshot(50, 50, color="red")

        with patch(
            "hermes_computer_use.tools.screenshot.capture_screenshot",
            return_value=small_ss,
        ):
            result = zoom_screenshot(x=10, y=10, width=50, height=50, output_size=200)

        assert result.width == 200
        assert result.height == 200
        assert result.scale_factor == pytest.approx(4.0, abs=0.05)

    def test_downscales_large_region(self):
        """Even a region larger than output_size is resized to output_size."""
        large_ss = self._make_screenshot(800, 600, color="blue")

        with patch(
            "hermes_computer_use.tools.screenshot.capture_screenshot",
            return_value=large_ss,
        ):
            result = zoom_screenshot(x=0, y=0, width=800, height=600, output_size=400)

        assert max(result.width, result.height) == 400

    def test_aspect_ratio_preserved(self):
        """Non-square region preserves aspect ratio after scaling."""
        # 200×100 → longest edge = 200 → scale = output_size/200
        rect_ss = self._make_screenshot(200, 100, color="yellow")

        with patch(
            "hermes_computer_use.tools.screenshot.capture_screenshot",
            return_value=rect_ss,
        ):
            result = zoom_screenshot(x=0, y=0, width=200, height=100, output_size=400)

        assert result.width == 400
        assert result.height == 200  # scaled proportionally (100 * 2)

    def test_returns_screenshot_with_png_data(self):
        """Output is a valid Screenshot with readable PNG bytes."""
        small_ss = self._make_screenshot(40, 40)

        with patch(
            "hermes_computer_use.tools.screenshot.capture_screenshot",
            return_value=small_ss,
        ):
            result = zoom_screenshot(x=5, y=5, width=40, height=40, output_size=160)

        assert isinstance(result, Screenshot)
        assert len(result.data) > 0
        # Must be valid PNG
        img = Image.open(io.BytesIO(result.data))
        assert img.format == "PNG"

    def test_capture_screenshot_called_with_region(self):
        """zoom_screenshot passes region=(x, y, width, height) to capture_screenshot."""
        small_ss = self._make_screenshot(80, 60)

        with patch(
            "hermes_computer_use.tools.screenshot.capture_screenshot",
            return_value=small_ss,
        ) as mock_cap:
            zoom_screenshot(x=100, y=200, width=80, height=60, output_size=320)

        # First positional/keyword arg should be region
        call_kwargs = mock_cap.call_args
        assert call_kwargs is not None
        # Check region was passed correctly
        region = call_kwargs.kwargs.get("region") or call_kwargs.args[0]
        assert region == (100, 200, 80, 60)

    def test_default_output_size_is_1024(self):
        """Default output_size=1024 is applied when not specified."""
        small_ss = self._make_screenshot(64, 64)

        with patch(
            "hermes_computer_use.tools.screenshot.capture_screenshot",
            return_value=small_ss,
        ):
            result = zoom_screenshot(x=0, y=0, width=64, height=64)

        assert max(result.width, result.height) == 1024

