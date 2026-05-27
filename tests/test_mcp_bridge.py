"""Tests for the FastMCP bridge that mounts /mcp onto NAT's FastAPI server."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workflow(response: str = "Screenshot taken.") -> AsyncMock:
    """Return a mock NAT Workflow whose ainvoke returns a react_agent-shaped dict."""
    workflow = AsyncMock()
    workflow.ainvoke.return_value = {
        "messages": [
            HumanMessage(content="do the thing"),
            AIMessage(content=response),
        ]
    }
    return workflow


def _make_builder(workflow: Any) -> AsyncMock:
    """Return a mock WorkflowBuilder whose build() returns the given workflow."""
    builder = AsyncMock()
    builder.build.return_value = workflow
    return builder


# ---------------------------------------------------------------------------
# Import guard — skip if NAT/fastmcp not installed
# ---------------------------------------------------------------------------

nat_langchain = pytest.importorskip(
    "nat.front_ends.fastapi.fastapi_front_end_plugin_worker",
    reason="nvidia-nat-langchain not installed",
)
fastmcp_mod = pytest.importorskip("fastmcp", reason="fastmcp not installed")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestMCPBridgeFrontEndWorker:

    def test_import(self):
        """Module and class are importable."""
        from hermes_computer_use.mcp_bridge import MCPBridgeFrontEndWorker
        assert MCPBridgeFrontEndWorker is not None

    def test_inherits_from_nat_worker(self):
        from hermes_computer_use.mcp_bridge import MCPBridgeFrontEndWorker
        from nat.front_ends.fastapi.fastapi_front_end_plugin_worker import FastApiFrontEndPluginWorker
        assert issubclass(MCPBridgeFrontEndWorker, FastApiFrontEndPluginWorker)

    @pytest.mark.asyncio
    async def test_add_routes_calls_super_and_mounts_mcp(self):
        """add_routes calls super().add_routes and mounts FastMCP at /mcp."""
        from hermes_computer_use.mcp_bridge import MCPBridgeFrontEndWorker

        workflow = _make_workflow()
        builder = _make_builder(workflow)

        app = MagicMock()
        app.mount = MagicMock()

        worker = object.__new__(MCPBridgeFrontEndWorker)

        with patch(
            "nat.front_ends.fastapi.fastapi_front_end_plugin_worker.FastApiFrontEndPluginWorker.add_routes",
            new_callable=AsyncMock,
        ) as mock_super:
            await worker.add_routes(app, builder)

        # super().add_routes was called
        mock_super.assert_awaited_once_with(app, builder)
        # workflow was built
        builder.build.assert_awaited_once()
        # /mcp was mounted
        app.mount.assert_called_once()
        mount_path = app.mount.call_args[0][0]
        assert mount_path == "/mcp"

    @pytest.mark.asyncio
    async def test_computer_use_tool_returns_last_ai_message(self):
        """The computer_use tool extracts the last AIMessage content."""
        from hermes_computer_use.mcp_bridge import MCPBridgeFrontEndWorker

        expected = "I clicked the button."
        workflow = _make_workflow(response=expected)
        builder = _make_builder(workflow)

        app = MagicMock()
        app.mount = MagicMock()

        worker = object.__new__(MCPBridgeFrontEndWorker)

        # Capture the registered tool by intercepting mcp.tool()
        registered_tools: dict[str, Any] = {}

        original_fastmcp = fastmcp_mod.FastMCP

        class CapturingFastMCP(original_fastmcp):
            def tool(self):
                decorator = super().tool()
                def capturing_decorator(fn: Any) -> Any:
                    registered_tools[fn.__name__] = fn
                    return decorator(fn)
                return capturing_decorator

        with patch("hermes_computer_use.mcp_bridge.fastmcp.FastMCP", CapturingFastMCP):
            with patch(
                "nat.front_ends.fastapi.fastapi_front_end_plugin_worker.FastApiFrontEndPluginWorker.add_routes",
                new_callable=AsyncMock,
            ):
                await worker.add_routes(app, builder)

        assert "computer_use" in registered_tools
        result = await registered_tools["computer_use"]("take a screenshot")
        assert result == expected

        # Verify workflow was called with a HumanMessage
        call_args = workflow.ainvoke.call_args[0][0]
        assert "messages" in call_args
        assert isinstance(call_args["messages"][0], HumanMessage)
        assert call_args["messages"][0].content == "take a screenshot"

    @pytest.mark.asyncio
    async def test_computer_use_tool_empty_messages_fallback(self):
        """Falls back to 'Task completed.' when messages list is empty."""
        from hermes_computer_use.mcp_bridge import MCPBridgeFrontEndWorker

        workflow = AsyncMock()
        workflow.ainvoke.return_value = {"messages": []}
        builder = _make_builder(workflow)

        app = MagicMock()
        app.mount = MagicMock()
        worker = object.__new__(MCPBridgeFrontEndWorker)

        registered_tools: dict[str, Any] = {}
        original_fastmcp = fastmcp_mod.FastMCP

        class CapturingFastMCP(original_fastmcp):
            def tool(self):
                decorator = super().tool()
                def capturing_decorator(fn: Any) -> Any:
                    registered_tools[fn.__name__] = fn
                    return decorator(fn)
                return capturing_decorator

        with patch("hermes_computer_use.mcp_bridge.fastmcp.FastMCP", CapturingFastMCP):
            with patch(
                "nat.front_ends.fastapi.fastapi_front_end_plugin_worker.FastApiFrontEndPluginWorker.add_routes",
                new_callable=AsyncMock,
            ):
                await worker.add_routes(app, builder)

        result = await registered_tools["computer_use"]("do something")
        assert result == "Task completed."

    @pytest.mark.asyncio
    async def test_computer_use_tool_missing_messages_key(self):
        """Falls back gracefully when workflow returns no 'messages' key."""
        from hermes_computer_use.mcp_bridge import MCPBridgeFrontEndWorker

        workflow = AsyncMock()
        workflow.ainvoke.return_value = {}
        builder = _make_builder(workflow)

        app = MagicMock()
        app.mount = MagicMock()
        worker = object.__new__(MCPBridgeFrontEndWorker)

        registered_tools: dict[str, Any] = {}
        original_fastmcp = fastmcp_mod.FastMCP

        class CapturingFastMCP(original_fastmcp):
            def tool(self):
                decorator = super().tool()
                def capturing_decorator(fn: Any) -> Any:
                    registered_tools[fn.__name__] = fn
                    return decorator(fn)
                return capturing_decorator

        with patch("hermes_computer_use.mcp_bridge.fastmcp.FastMCP", CapturingFastMCP):
            with patch(
                "nat.front_ends.fastapi.fastapi_front_end_plugin_worker.FastApiFrontEndPluginWorker.add_routes",
                new_callable=AsyncMock,
            ):
                await worker.add_routes(app, builder)

        result = await registered_tools["computer_use"]("do something")
        assert result == "Task completed."
