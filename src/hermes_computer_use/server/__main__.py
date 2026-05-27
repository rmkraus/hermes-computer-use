"""Unified server entrypoint — MCP + OpenAI API on a single port.

Usage (inside the container or bare metal):

    python -m hermes_computer_use.server        # MCP + OpenAI on port 8000
    python -m hermes_computer_use.server --port 8080
    python -m hermes_computer_use.server --mcp-only
    python -m hermes_computer_use.server --openai-only

Environment variables:
    COMPUTER_USE_PORT      Server port (default: 8000)
    COMPUTER_USE_HOST      Bind host (default: 0.0.0.0)
    COMPUTER_USE_MODEL     LLM model string (default: openai:gpt-4o)
    OPENAI_API_KEY         Required for the default model
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from hermes_computer_use.server.mcp_server import create_mcp_server
from hermes_computer_use.server.openai_server import router as openai_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def _build_combined_app():
    """Mount both MCP and OpenAI API under one ASGI app."""
    mcp = create_mcp_server()
    mcp_http = mcp.http_app()

    # FastMCP's StreamableHTTP transport needs its lifespan initialised.
    # Wire it into the parent app via a forwarding lifespan context manager.
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        async with mcp_http.lifespan(app):
            yield

    combined = FastAPI(
        title="Hermes Computer Use",
        description="Ubuntu desktop automation — MCP + OpenAI API",
        version="0.3.0",
        lifespan=lifespan,
    )

    # Include OpenAI-compat routes (health, /v1/models, /v1/chat/completions)
    combined.include_router(openai_router)

    # Mount MCP ASGI app at "/" — FastMCP's http_app() puts its route at /mcp
    combined.mount("/", mcp_http)

    return combined


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Hermes Computer Use server")
    parser.add_argument("--host", default=os.environ.get("COMPUTER_USE_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("COMPUTER_USE_PORT", "8000")))
    parser.add_argument("--mcp-only", action="store_true", help="Serve only the MCP endpoint")
    parser.add_argument("--openai-only", action="store_true", help="Serve only the OpenAI API")
    parser.add_argument("--reload", action="store_true", help="Enable hot-reload (dev mode)")
    args = parser.parse_args(argv)

    if args.mcp_only:
        mcp = create_mcp_server()
        logger.info("Starting MCP-only server on %s:%d/mcp", args.host, args.port)
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    elif args.openai_only:
        logger.info("Starting OpenAI-only server on %s:%d", args.host, args.port)
        uvicorn.run(
            "hermes_computer_use.server.openai_server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    else:
        logger.info("Starting combined MCP+OpenAI server on %s:%d", args.host, args.port)
        app = _build_combined_app()
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
        )


if __name__ == "__main__":
    main(sys.argv[1:])
