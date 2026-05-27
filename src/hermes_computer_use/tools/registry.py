"""Tool registration — discovers available tools and their capabilities."""

from __future__ import annotations

import importlib.util
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCapability:
    """A single tool capability exposed by the toolkit."""

    name: str
    description: str
    requires_display: bool = True
    dependencies: list[str] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in self.dependencies:
            if not importlib.util.find_spec(dep):
                return False
        if self.requires_display:
            return self._has_display_server()
        return True

    def _has_display_server(self) -> bool:
        """Check if a display server (X11/Wayland) is available."""
        return bool(os.environ.get("DISPLAY")) or bool(
            os.environ.get("WAYLAND_DISPLAY")
        )


# Registry of all available tool capabilities
TOOLS: dict[str, ToolCapability] = {}


def register_tool(capability: ToolCapability) -> None:
    """Register a tool capability in the global registry."""
    TOOLS[capability.name] = capability
    logger.debug("Registered tool: %s", capability.name)


def list_tools() -> list[ToolCapability]:
    """Return all registered tool capabilities."""
    return list(TOOLS.values())


def list_available_tools() -> list[ToolCapability]:
    """Return only tools that are currently available."""
    return [t for t in TOOLS.values() if t.is_available]


# --- Built-in tool definitions ---

register_tool(
    ToolCapability(
        name="screenshot",
        description="Capture a screenshot of the current screen. Returns base64-encoded PNG image.",
        requires_display=True,
        dependencies=["PIL"],
    )
)

register_tool(
    ToolCapability(
        name="input_mouse",
        description="Simulate mouse input: click, move, scroll. Supports left/right/middle clicks, scrolling, and absolute positioning.",
        requires_display=True,
        dependencies=["pyautogui", "PIL"],
    )
)

register_tool(
    ToolCapability(
        name="input_keyboard",
        description="Simulate keyboard input: type text, press keys, send key combinations (e.g., ctrl+c).",
        requires_display=True,
        dependencies=["pyautogui"],
    )
)

register_tool(
    ToolCapability(
        name="window_manage",
        description="Window management: list open windows, focus a window, get window info, move/resize windows.",
        requires_display=True,
        dependencies=[],
    )
)

register_tool(
    ToolCapability(
        name="app_launch",
        description="Launch applications by name or command. Open files, URLs, or system applications.",
        requires_display=True,
        dependencies=["pyautogui"],
    )
)

register_tool(
    ToolCapability(
        name="action_sequence",
        description="Execute a sequence of actions (click, type, wait) in a single call for multi-step tasks.",
        requires_display=True,
        dependencies=["pyautogui", "Pillow"],
    )
)

register_tool(
    ToolCapability(
        name="vision_inference",
        description="Send a screenshot to a vision model (Anthropic/OpenAI/local) and get reasoning + action recommendations.",
        requires_display=False,
        dependencies=["requests"],
    )
)


def get_tool_schema(tool_name: str) -> dict[str, Any] | None:
    """Get the OpenAI tool schema for a named tool, for integration with LLM APIs."""
    if tool_name not in TOOLS:
        return None

    tool = TOOLS[tool_name]

    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }


def get_all_tool_schemas() -> list[dict[str, Any]]:
    """Get OpenAI tool schemas for all available tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": cap.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
        for name, cap in TOOLS.items()
        if cap.is_available
    ]
