"""Tests for tool registry and capability definitions."""

from __future__ import annotations

import importlib.util
from unittest.mock import patch

import pytest

from hermes_computer_use.tools.registry import (
    ToolCapability,
    get_all_tool_schemas,
    get_tool_schema,
    list_available_tools,
    list_tools,
    register_tool,
    TOOLS,
)


class TestToolCapability:
    """Tests for ToolCapability dataclass."""

    def test_capability_creation(self):
        """Test creating a ToolCapability with defaults."""
        cap = ToolCapability(
            name="test_tool",
            description="A test tool",
        )
        assert cap.name == "test_tool"
        assert cap.description == "A test tool"
        assert cap.requires_display is True
        assert cap.dependencies == []

    def test_capability_with_all_fields(self):
        """Test creating a ToolCapability with all fields specified."""
        cap = ToolCapability(
            name="no_display_tool",
            description="Tool that doesn't need a display",
            requires_display=False,
            dependencies=["requests", "json"],
        )
        assert cap.requires_display is False
        assert cap.dependencies == ["requests", "json"]

    def test_is_available_with_missing_dependency(self):
        """Test is_available returns False when dependency is missing."""
        cap = ToolCapability(
            name="missing_dep_tool",
            description="Tool with missing dependency",
            dependencies=["nonexistent_package_12345"],
        )
        assert cap.is_available is False

    def test_is_available_with_existing_dependency(self):
        """Test is_available returns True when all deps exist."""
        # Use the importable module name (PIL), not the package name (Pillow)
        cap = ToolCapability(
            name="pillow_tool",
            description="Tool using Pillow",
            requires_display=False,
            dependencies=["PIL"],
        )
        assert cap.is_available is True

    def test_is_available_requires_display_false(self):
        """Test is_available when display not required."""
        cap = ToolCapability(
            name="no_display",
            description="No display needed",
            requires_display=False,
        )
        # Should be available regardless of DISPLAY env
        assert cap.is_available is True


class TestToolRegistry:
    """Tests for tool registration."""

    def test_list_tools(self):
        """Test listing all registered tools."""
        tools = list_tools()
        assert len(tools) > 0
        assert all(isinstance(t, ToolCapability) for t in tools)

    def test_get_all_tool_schemas(self):
        """Test getting all tool schemas."""
        schemas = get_all_tool_schemas()
        assert len(schemas) > 0
        for schema in schemas:
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            func = schema["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_get_tool_schema(self):
        """Test getting a specific tool schema."""
        schema = get_tool_schema("screenshot")
        assert schema is not None
        assert schema["function"]["name"] == "screenshot"
        assert "screenshot" in schema["function"]["description"]

    def test_get_tool_schema_unknown(self):
        """Test getting schema for unknown tool returns None."""
        assert get_tool_schema("nonexistent_tool") is None

    def test_list_available_tools(self):
        """Test listing only available tools."""
        available = list_available_tools()
        assert len(available) <= len(list_tools())
        assert all(t.is_available for t in available)

    def test_register_tool(self):
        """Test registering a new tool."""
        initial_count = len(TOOLS)
        new_cap = ToolCapability(
            name="custom_test_tool",
            description="Custom test tool",
            requires_display=False,
        )
        register_tool(new_cap)
        assert len(TOOLS) > initial_count
        assert "custom_test_tool" in TOOLS
        assert TOOLS["custom_test_tool"].description == "Custom test tool"


class TestBuiltInTools:
    """Tests for built-in tool capabilities."""

    def test_screenshot_registered(self):
        """Test screenshot tool is registered."""
        assert "screenshot" in TOOLS
        assert TOOLS["screenshot"].requires_display is True
        assert "Pillow" in TOOLS["screenshot"].dependencies

    def test_input_mouse_registered(self):
        """Test input_mouse tool is registered."""
        assert "input_mouse" in TOOLS
        assert TOOLS["input_mouse"].requires_display is True
        assert "pyautogui" in TOOLS["input_mouse"].dependencies

    def test_input_keyboard_registered(self):
        """Test input_keyboard tool is registered."""
        assert "input_keyboard" in TOOLS
        assert TOOLS["input_keyboard"].requires_display is True
        assert "pyautogui" in TOOLS["input_keyboard"].dependencies

    def test_window_manage_registered(self):
        """Test window_manage tool is registered."""
        assert "window_manage" in TOOLS
        assert TOOLS["window_manage"].requires_display is True

    def test_app_launch_registered(self):
        """Test app_launch tool is registered."""
        assert "app_launch" in TOOLS
        assert TOOLS["app_launch"].requires_display is True

    def test_action_sequence_registered(self):
        """Test action_sequence tool is registered."""
        assert "action_sequence" in TOOLS

    def test_vision_inference_registered(self):
        """Test vision_inference tool is registered (no display required)."""
        assert "vision_inference" in TOOLS
        assert TOOLS["vision_inference"].requires_display is False
