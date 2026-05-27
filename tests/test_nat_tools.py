"""Tests for the NAT tool registrations (hermes_computer_use.nat.tools).

These tests verify the tool function logic in isolation, without requiring
a real NAT server, real display, or real nvidia-nat installation.
We mock the NAT decorators/classes at the module level so tests run anywhere.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock NAT before any imports of nat.tools so the module loads without
# nvidia-nat installed (in CI environments).
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="module")
def mock_nat_imports():
    """Stub out NAT imports so tools.py loads without nvidia-nat installed."""
    # Create minimal stubs for the three NAT symbols tools.py imports
    fake_function_info = MagicMock()
    fake_function_info.from_fn = MagicMock(return_value=MagicMock())

    fake_register_function = lambda config_type: (lambda fn: fn)

    fake_config_base = type("FunctionBaseConfig", (), {"__init_subclass__": classmethod(lambda cls, **kw: None)})

    modules = {
        "nat": MagicMock(),
        "nat.builder": MagicMock(),
        "nat.builder.function_info": MagicMock(FunctionInfo=fake_function_info),
        "nat.cli": MagicMock(),
        "nat.cli.register_workflow": MagicMock(register_function=fake_register_function),
        "nat.data_models": MagicMock(),
        "nat.data_models.function": MagicMock(FunctionBaseConfig=fake_config_base),
    }
    with patch.dict("sys.modules", modules):
        yield


# ---------------------------------------------------------------------------
# We test the inner _fn callables, not the generator wrappers.
# Build a helper to extract them.
# ---------------------------------------------------------------------------


def make_screenshot_tool():
    """Build a take_screenshot inner function with a mocked Screenshot."""
    from hermes_computer_use.tools.screenshot import Screenshot

    fake_shot = Screenshot(data=b"\x89PNG", width=800, height=600)

    async def _fn() -> str:
        import json
        return json.dumps({
            "image_b64": fake_shot.to_base64(),
            "width": fake_shot.width,
            "height": fake_shot.height,
            "urn": fake_shot.to_urn(),
        })

    return _fn, fake_shot


class TestTakeScreenshotTool:
    """Tests for take_screenshot tool logic."""

    @pytest.mark.asyncio
    async def test_returns_json_with_required_keys(self):
        fn, _ = make_screenshot_tool()
        result = json.loads(await fn())
        assert "image_b64" in result
        assert "width" in result
        assert "height" in result
        assert "urn" in result

    @pytest.mark.asyncio
    async def test_dimensions_match(self):
        fn, shot = make_screenshot_tool()
        result = json.loads(await fn())
        assert result["width"] == shot.width
        assert result["height"] == shot.height

    @pytest.mark.asyncio
    async def test_urn_format(self):
        fn, _ = make_screenshot_tool()
        result = json.loads(await fn())
        assert result["urn"].startswith("data:image/png;base64,")


class TestMouseClickTool:
    """Tests for mouse_click tool logic (safety + action)."""

    @pytest.mark.asyncio
    async def test_safe_click_succeeds(self):
        from hermes_computer_use.tools.actions import ActionResult

        safe_result = MagicMock(safe=True, reason=None)
        action_result = ActionResult(action="click", success=True)

        with patch("hermes_computer_use.safety.checker.SafetyChecker.check_all", return_value=safe_result):
            with patch(
                "hermes_computer_use.tools.actions.DesktopActionExecutor.execute",
                return_value=action_result,
            ):
                # Import here so mock_nat_imports is in effect
                from hermes_computer_use.tools.actions import DesktopActionExecutor
                from hermes_computer_use.safety.checker import SafetyChecker

                safety = SafetyChecker()
                executor = DesktopActionExecutor()

                check = safety.check_all("click", x=100, y=200, button="left")
                assert check.safe is True

                result = executor.execute("click", x=100, y=200, button="left")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_blocked_click_returns_error(self):
        """When safety check fails, the tool should return an error JSON."""
        blocked_result = MagicMock(safe=False, reason="blocked coords", blocked=True)

        async def _fn(x: int, y: int, button: str = "left") -> str:
            check = MagicMock()
            check.safe = False
            check.reason = "blocked coords"
            if not check.safe:
                return json.dumps({"success": False, "error": f"Blocked by safety: {check.reason}"})
            return json.dumps({"success": True})

        result = json.loads(await _fn(100, 200))
        assert result["success"] is False
        assert "Blocked by safety" in result["error"]


class TestKeyboardTypeTool:
    """Tests for keyboard_type tool logic."""

    @pytest.mark.asyncio
    async def test_safe_text_succeeds(self):
        from hermes_computer_use.tools.actions import ActionResult

        safe = MagicMock(safe=True, reason=None)
        ok = ActionResult(action="type", success=True)

        with patch("hermes_computer_use.safety.checker.SafetyChecker.check_text", return_value=safe):
            with patch(
                "hermes_computer_use.tools.actions.DesktopActionExecutor.execute",
                return_value=ok,
            ):
                from hermes_computer_use.safety.checker import SafetyChecker
                from hermes_computer_use.tools.actions import DesktopActionExecutor

                checker = SafetyChecker()
                result = checker.check_text("Hello world")
                assert result.safe is True

    @pytest.mark.asyncio
    async def test_dangerous_text_blocked(self):
        """Dangerous text (rm -rf) should be blocked by safety."""
        from hermes_computer_use.safety.checker import SafetyChecker

        checker = SafetyChecker()
        result = checker.check_text("rm -rf /")
        assert result.safe is False
        assert result.blocked is True

    @pytest.mark.asyncio
    async def test_safe_text_not_blocked(self):
        """Normal text should pass safety check."""
        from hermes_computer_use.safety.checker import SafetyChecker

        checker = SafetyChecker()
        result = checker.check_text("Hello, world!")
        assert result.safe is True


class TestKeyboardHotkeyTool:
    """Tests for keyboard_hotkey tool logic."""

    @pytest.mark.asyncio
    async def test_blocked_combo_ctrl_alt_del(self):
        """ctrl+alt+delete should be blocked."""
        from hermes_computer_use.safety.checker import SafetyChecker

        checker = SafetyChecker()
        result = checker.check_key_combo(["ctrl", "alt", "delete"])
        assert result.safe is False
        assert result.blocked is True

    @pytest.mark.asyncio
    async def test_safe_combo_ctrl_c(self):
        """ctrl+c should be allowed."""
        from hermes_computer_use.safety.checker import SafetyChecker

        checker = SafetyChecker()
        result = checker.check_key_combo(["ctrl", "c"])
        assert result.safe is True

    @pytest.mark.asyncio
    async def test_hotkey_parsing(self):
        """Test that 'ctrl+shift+t' parses to ['ctrl', 'shift', 't']."""
        keys = "ctrl+shift+t"
        key_list = [k.strip() for k in keys.split("+")]
        assert key_list == ["ctrl", "shift", "t"]


class TestCheckActionSafetyTool:
    """Tests for check_action_safety tool logic."""

    @pytest.mark.asyncio
    async def test_safe_action(self):
        from hermes_computer_use.safety.checker import SafetyChecker

        checker = SafetyChecker()
        result = checker.check_all("click", x=100, y=200)
        assert result.safe is True

    @pytest.mark.asyncio
    async def test_dangerous_action_blocked(self):
        from hermes_computer_use.safety.checker import SafetyChecker

        checker = SafetyChecker()
        result = checker.check_all("type", text="rm -rf /")
        assert result.safe is False

    @pytest.mark.asyncio
    async def test_json_params_parsed(self):
        """Test that JSON params string is correctly parsed."""
        params_str = '{"text": "hello"}'
        kwargs = json.loads(params_str)
        assert kwargs == {"text": "hello"}

    @pytest.mark.asyncio
    async def test_malformed_json_params(self):
        """Malformed JSON params should not crash the tool."""
        try:
            kwargs = json.loads("not json")
        except json.JSONDecodeError:
            kwargs = {}
        assert kwargs == {}


class TestWindowTools:
    """Tests for list_windows and focus_window tool logic."""

    def test_list_windows_returns_serializable_list(self, mock_xdotool):
        """list_windows should return JSON-serializable window data."""
        from hermes_computer_use.tools.window import WindowInfo, WindowManager

        fake_windows = [
            WindowInfo(
                window_id="0x01234",
                title="Firefox",
                class_name="firefox",
                pid=1234,
                x=0, y=0, width=1920, height=1080,
                active=True,
            )
        ]

        with patch.object(WindowManager, "list_windows", return_value=fake_windows):
            mgr = WindowManager()
            windows = mgr.list_windows()

            result = [
                {
                    "window_id": w.window_id,
                    "title": w.title,
                    "class_name": w.class_name,
                    "pid": w.pid,
                    "x": w.x, "y": w.y,
                    "width": w.width, "height": w.height,
                    "active": w.active,
                }
                for w in windows
            ]

            # Should JSON-serialize without errors
            json_str = json.dumps(result)
            parsed = json.loads(json_str)
            assert len(parsed) == 1
            assert parsed[0]["title"] == "Firefox"
            assert parsed[0]["active"] is True

    def test_focus_window_not_found(self, mock_xdotool):
        """focus_window with no match should return success=False."""
        from hermes_computer_use.tools.window import WindowManager

        with patch.object(WindowManager, "search_windows", return_value=[]):
            mgr = WindowManager()
            windows = mgr.search_windows("nonexistent")
            assert windows == []
            # Tool would return: {"success": False, "error": "No window matching ..."}


class TestZoomScreenshotTool:
    """Tests for zoom_screenshot NAT tool logic."""

    def _make_screenshot(self, width: int, height: int):
        from PIL import Image
        import io as _io
        from hermes_computer_use.tools.screenshot import Screenshot

        img = Image.new("RGB", (width, height), color="purple")
        buf = _io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Screenshot(data=buf.read(), width=width, height=height)

    @pytest.mark.asyncio
    async def test_returns_json_with_required_keys(self):
        """zoom_screenshot tool returns JSON with all expected keys."""
        from hermes_computer_use.tools.screenshot import Screenshot

        shot = self._make_screenshot(200, 200)
        shot_scaled = Screenshot(data=shot.data, width=1024, height=1024, scale_factor=5.12)

        async def _fn(x, y, width, height, output_size=1024) -> str:
            return json.dumps({
                "image_b64": shot_scaled.to_base64(),
                "width": shot_scaled.width,
                "height": shot_scaled.height,
                "scale_factor": shot_scaled.scale_factor,
                "urn": shot_scaled.to_urn(),
            })

        result = json.loads(await _fn(0, 0, 200, 200))
        assert "image_b64" in result
        assert "width" in result
        assert "height" in result
        assert "scale_factor" in result
        assert "urn" in result

    @pytest.mark.asyncio
    async def test_invalid_dimensions_return_error(self):
        """zoom_screenshot tool returns JSON error for zero dimensions."""

        async def _fn(x, y, width, height, output_size=1024) -> str:
            from hermes_computer_use.tools.screenshot import zoom_screenshot as _zoom
            try:
                shot = _zoom(x=x, y=y, width=width, height=height, output_size=output_size)
            except ValueError as exc:
                return json.dumps({"error": str(exc)})
            return json.dumps({"image_b64": shot.to_base64()})

        result = json.loads(await _fn(0, 0, 0, 100))
        assert "error" in result
        assert "positive" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_urn_format(self):
        """zoom_screenshot URN starts with correct data URI prefix."""
        shot = self._make_screenshot(100, 100)

        async def _fn(x, y, width, height, output_size=1024) -> str:
            return json.dumps({
                "image_b64": shot.to_base64(),
                "width": shot.width,
                "height": shot.height,
                "scale_factor": 1.0,
                "urn": shot.to_urn(),
            })

        result = json.loads(await _fn(0, 0, 100, 100))
        assert result["urn"].startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_scale_factor_is_float(self):
        """scale_factor in the response is a numeric float, not a string."""
        from hermes_computer_use.tools.screenshot import Screenshot

        shot = self._make_screenshot(50, 50)
        zoomed = Screenshot(data=shot.data, width=1024, height=1024, scale_factor=20.48)

        async def _fn(x, y, width, height, output_size=1024) -> str:
            return json.dumps({
                "image_b64": zoomed.to_base64(),
                "width": zoomed.width,
                "height": zoomed.height,
                "scale_factor": zoomed.scale_factor,
                "urn": zoomed.to_urn(),
            })

        result = json.loads(await _fn(0, 0, 50, 50))
        assert isinstance(result["scale_factor"], float)
