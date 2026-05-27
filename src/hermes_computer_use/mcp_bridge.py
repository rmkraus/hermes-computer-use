"""MCP bridge — mounts a FastMCP server onto NAT's FastAPI app.

Exposes a single ``computer_use`` MCP tool that invokes the NAT react_agent
in-process.  Both the OpenAI-compatible API (``/v1/chat/completions``) and the
MCP endpoint (``/mcp``) are served on the same port from the same process.

Usage
-----
Set the environment variable before starting NAT::

    NAT_FRONT_END_WORKER=hermes_computer_use.mcp_bridge:MCPBridgeFrontEndWorker
    nat serve --config_file workflow.yaml

Or via docker-entrypoint.sh (already set when using the provided image).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import fastmcp
from langchain_core.messages import HumanMessage

from nat.builder.workflow_builder import WorkflowBuilder
from nat.front_ends.fastapi.fastapi_front_end_plugin_worker import FastApiFrontEndPluginWorker

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


class MCPBridgeFrontEndWorker(FastApiFrontEndPluginWorker):
    """NAT FastAPI worker that additionally mounts a FastMCP server at ``/mcp``.

    Inherits all OpenAI-compatible routes from the parent class, then mounts a
    FastMCP ASGI sub-application that exposes the NAT workflow as a single
    ``computer_use`` MCP tool.
    """

    async def add_routes(self, app: FastAPI, builder: WorkflowBuilder) -> None:
        # All standard NAT routes first (/v1/chat/completions, /health, etc.)
        await super().add_routes(app, builder)

        # Build the workflow so we can call it directly (no HTTP round-trip).
        workflow = await builder.build()

        # --- FastMCP server -------------------------------------------------
        mcp = fastmcp.FastMCP(
            name="hermes-computer-use",
            instructions=(
                "Desktop automation agent for Ubuntu. "
                "Use the computer_use tool to control the desktop in natural language."
            ),
        )

        @mcp.tool()
        async def computer_use(instruction: str) -> str:
            """Control the Ubuntu desktop using natural language.

            Describe the task you want performed on the desktop. The agent will
            take screenshots, move the mouse, type text, run commands, and
            manage windows as needed to complete the task.

            Args:
                instruction: What you want done on the desktop.

            Returns:
                A description of what was done and the current desktop state.
            """
            logger.debug("MCP computer_use invoked: %s", instruction[:120])
            result = await workflow.ainvoke(
                {"messages": [HumanMessage(content=instruction)]}
            )
            # react_agent returns {"messages": [...]} — pull the last AI message
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                return str(last.content) if hasattr(last, "content") else str(last)
            return "Task completed."

        # Mount FastMCP's ASGI app at /mcp
        app.mount("/mcp", mcp.http_app)
        logger.info("FastMCP server mounted at /mcp")
