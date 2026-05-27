"""Tests for the MCP server layer."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestMCPServerCreation:
    def test_create_mcp_server_returns_instance(self):
        """create_mcp_server() should return a FastMCP instance."""
        fastmcp_mock = MagicMock()
        server_mock = MagicMock()
        fastmcp_mock.FastMCP.return_value = server_mock

        with patch.dict("sys.modules", {"fastmcp": fastmcp_mock}):
            from hermes_computer_use.server import mcp_server
            import importlib
            importlib.reload(mcp_server)
            result = mcp_server.create_mcp_server()

        fastmcp_mock.FastMCP.assert_called_once()
        assert result is server_mock

    def test_run_computer_use_tool_registered(self):
        """The MCP server must register a tool named 'run_computer_use'."""
        fastmcp_mock = MagicMock()
        server_mock = MagicMock()
        fastmcp_mock.FastMCP.return_value = server_mock

        tool_kwargs_captured: dict = {}

        def capture_tool(*args, **kwargs):
            tool_kwargs_captured.update(kwargs)
            def decorator(fn):
                return fn
            return decorator

        server_mock.tool = capture_tool

        with patch.dict("sys.modules", {"fastmcp": fastmcp_mock}):
            import importlib
            from hermes_computer_use.server import mcp_server
            importlib.reload(mcp_server)
            mcp_server.create_mcp_server()

        assert tool_kwargs_captured.get("name") == "run_computer_use"
        assert "desktop" in tool_kwargs_captured.get("description", "").lower()


class TestInvokeAgent:
    """Test _invoke_agent directly — no MCP server needed."""

    def test_returns_agent_response(self):
        from hermes_computer_use.server import mcp_server
        import importlib
        importlib.reload(mcp_server)

        fake_agent = MagicMock()
        fake_msg = MagicMock()
        fake_msg.content = "Done clicking!"
        fake_agent.invoke.return_value = {"messages": [fake_msg]}

        with patch.object(mcp_server, "_agent_cache", {"agent": fake_agent}):
            result = mcp_server._invoke_agent("Take a screenshot")

        assert "Done clicking!" in result
        fake_agent.invoke.assert_called_once()

    def test_returns_error_on_exception(self):
        from hermes_computer_use.server import mcp_server
        import importlib
        importlib.reload(mcp_server)

        bad_agent = MagicMock()
        bad_agent.invoke.side_effect = RuntimeError("LLM timeout")

        with patch.object(mcp_server, "_agent_cache", {"agent": bad_agent}):
            result = mcp_server._invoke_agent("Do something")

        assert "error" in result.lower() or "LLM timeout" in result

    def test_returns_fallback_on_empty_messages(self):
        from hermes_computer_use.server import mcp_server
        import importlib
        importlib.reload(mcp_server)

        empty_agent = MagicMock()
        empty_agent.invoke.return_value = {"messages": []}

        with patch.object(mcp_server, "_agent_cache", {"agent": empty_agent}):
            result = mcp_server._invoke_agent("Do nothing")

        assert "no response" in result.lower() or len(result) > 0

    def test_strips_image_parts_from_multipart(self):
        from hermes_computer_use.server import mcp_server
        import importlib
        importlib.reload(mcp_server)

        fake_agent = MagicMock()
        fake_msg = MagicMock()
        fake_msg.content = [
            {"type": "text", "text": "Here is what I see."},
            {"type": "image_url", "image_url": "data:image/png;base64,abc"},
        ]
        fake_agent.invoke.return_value = {"messages": [fake_msg]}

        with patch.object(mcp_server, "_agent_cache", {"agent": fake_agent}):
            result = mcp_server._invoke_agent("Show me the screen")

        assert "Here is what I see." in result
        assert "image_url" not in result
        assert "base64" not in result
