#!/usr/bin/env bash
# docker-entrypoint.sh — starts Xvfb then the NAT server
#
# Usage:
#   docker run IMAGE [openai|mcp] [NAT_ARGS...]
#
#   openai   Run NAT with the OpenAI-compatible FastAPI frontend (default)
#            Port: COMPUTER_USE_PORT (default 8000)
#            Passes remaining args to: nat serve --config_file workflow.yaml
#
#   mcp      Run NAT with the MCP frontend
#            Port: COMPUTER_USE_PORT (default 9901)
#            Passes remaining args to: nat start --config_file workflow-mcp.yaml
#
# Additional NAT args are passed through verbatim, e.g.:
#   docker run IMAGE openai --workers 2
#   docker run IMAGE mcp --override llms.agent.model meta/llama-4-scout-17b-16e-instruct
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

# ── Frontend selection ───────────────────────────────────────────────────────
# Peek at the first argument. If it's "openai" or "mcp", consume it and route
# accordingly. Anything else (or nothing) defaults to openai.
MODE="openai"
if [ $# -gt 0 ]; then
    case "$1" in
        openai|mcp)
            MODE="$1"
            shift
            ;;
    esac
fi

case "$MODE" in
    openai)
        echo "Starting NAT OpenAI frontend on port ${COMPUTER_USE_PORT:-8000}..."
        exec nat serve --config_file /app/workflow.yaml "$@"
        ;;
    mcp)
        echo "Starting NAT MCP frontend on port ${COMPUTER_USE_PORT:-9901}..."
        exec nat start --config_file /app/workflow-mcp.yaml "$@"
        ;;
esac
