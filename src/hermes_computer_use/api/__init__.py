"""Direct REST API for individual tool calls.

Exposes /v1/tools/{tool_name} POST endpoints so clients (like Hermes Agent's
nat_backend.py) can invoke individual desktop tools without going through the
full NAT react_agent loop.

Also exposes:
  GET  /health        — liveness probe
  GET  /v1/tools      — list available tools + their parameter schemas

Start alongside the NAT server via the Dockerfile entrypoint,
or standalone with:
  uvicorn hermes_computer_use.api.app:app --host 0.0.0.0 --port 8001
"""
