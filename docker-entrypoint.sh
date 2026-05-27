#!/usr/bin/env bash
# docker-entrypoint.sh — starts Xvfb then the NAT OpenAI server
#
# Usage:
#   docker run IMAGE [NAT_ARGS...]
#
# Any arguments are passed directly to: nat serve --config_file workflow.yaml
# Example:
#   docker run IMAGE --override llms.agent.model meta/llama-4-scout-17b-16e-instruct
#
set -euo pipefail

# ── Virtual framebuffer ──────────────────────────────────────────────────────
DISPLAY_NUM="${DISPLAY_NUM:-99}"
DISPLAY=":${DISPLAY_NUM}"
export DISPLAY

rm -f "/tmp/.X${DISPLAY_NUM}-lock"
rm -rf "/tmp/.X11-unix/X${DISPLAY_NUM}"

Xvfb "${DISPLAY}" -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

echo "Waiting for Xvfb on ${DISPLAY}..."
TIMEOUT=15
ELAPSED=0
until [ -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ]; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "ERROR: Xvfb did not start within ${TIMEOUT}s" >&2
        exit 1
    fi
    sleep 0.5
    ELAPSED=$((ELAPSED + 1))
done
echo "Xvfb ready."

cleanup() {
    echo "Shutting down Xvfb..."
    kill "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ── Start NAT server (OpenAI API + MCP bridge on /mcp) ──────────────────────
export NAT_FRONT_END_WORKER=hermes_computer_use.mcp_bridge:MCPBridgeFrontEndWorker
echo "Starting NAT server on port ${COMPUTER_USE_PORT:-8000}..."
echo "  OpenAI API : /v1/chat/completions"
echo "  MCP        : /mcp"
exec nat serve --config_file /app/workflow.yaml "$@"
