"""Server module — lazy imports to keep startup fast without optional deps."""

__all__ = ["create_mcp_server", "openai_app"]


def create_mcp_server():
    from hermes_computer_use.server.mcp_server import create_mcp_server as _create
    return _create()


def openai_app():
    from hermes_computer_use.server.openai_server import app
    return app
