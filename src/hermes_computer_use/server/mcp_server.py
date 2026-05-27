"""MCP server that exposes the computer-use DeepAgent as a single MCP tool.

The agent is wrapped as one MCP tool — ``run_computer_use`` — so any MCP
client (Hermes, Claude Desktop, Cursor, etc.) can invoke the full agent loop
with a single natural-language goal string.

Transport: FastMCP Streamable HTTP (default) or stdio.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Module-level cache so the agent is initialised once and tests can patch it.
_agent_cache: dict[str, Any] = {}


def _get_agent() -> Any:
    """Lazily initialise and cache the DeepAgent."""
    if "agent" not in _agent_cache:
        from hermes_computer_use.agent.graph import create_computer_use_agent  # noqa: PLC0415
        _agent_cache["agent"] = create_computer_use_agent()
        logger.info("DeepAgent initialised")
    return _agent_cache["agent"]


def _invoke_agent(goal: str) -> str:
    """Run the agent and extract the final text response."""
    agent = _get_agent()
    try:
        result = agent.invoke({"messages": goal})
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            if hasattr(last, "content"):
                content = last.content
                if isinstance(content, list):
                    parts = [
                        p["text"] if isinstance(p, dict) else str(p)
                        for p in content
                        if not (isinstance(p, dict) and p.get("type") == "image_url")
                    ]
                    return "\n".join(parts)
                return str(content)
            return str(last)
        return "Agent completed with no response."
    except Exception as exc:
        logger.exception("Agent invocation failed")
        return f"Agent error: {exc}"


def create_mcp_server() -> Any:
    """Build and return a FastMCP server with the computer-use agent tool.

    Returns:
        A :class:`fastmcp.FastMCP` instance.
    """
    from fastmcp import FastMCP  # noqa: PLC0415

    mcp = FastMCP(
        name="hermes-computer-use",
        instructions=(
            "Ubuntu desktop automation agent. "
            "Use `run_computer_use` to control the desktop — take screenshots, "
            "click, type, run commands, manage windows, and complete multi-step tasks."
        ),
    )

    @mcp.tool(
        name="run_computer_use",
        description=(
            "Execute a desktop automation goal on the Ubuntu desktop. "
            "The agent will take screenshots, click, type, run shell commands, "
            "manage windows, and do whatever is needed to complete the task. "
            "Describe your goal in plain English."
        ),
    )
    def run_computer_use(goal: str) -> str:
        """Run the computer-use DeepAgent to completion for the given goal."""
        return _invoke_agent(goal)

    return mcp
