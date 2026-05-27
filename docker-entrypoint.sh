#!/bin/bash
# docker-entrypoint.sh — start Xvfb virtual display, tool REST API, and NAT server

set -e

DISPLAY_NUM="${DISPLAY_NUM:-1}"
SCREEN_RESOLUTION="${SCREEN_RESOLUTION:-1920x1080x24}"
TOOL_API_PORT="${TOOL_API_PORT:-8001}"

echo "==> Starting Xvfb virtual display :${DISPLAY_NUM} at ${SCREEN_RESOLUTION}"
Xvfb ":${DISPLAY_NUM}" -screen 0 "${SCREEN_RESOLUTION}" &
XVFB_PID=$!

export DISPLAY=":${DISPLAY_NUM}"

# Wait for Xvfb to be ready
sleep 1
if ! xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
    echo "ERROR: Xvfb did not start on ${DISPLAY}"
    exit 1
fi

# Start a minimal window manager so windows can be focused/managed
if command -v xfwm4 &>/dev/null; then
    echo "==> Starting xfwm4 window manager"
    xfwm4 --daemon --display "${DISPLAY}" 2>/dev/null || true
fi

# Start the direct tool REST API on port 8001
echo "==> Starting tool REST API on port ${TOOL_API_PORT}"
uvicorn hermes_computer_use.api.app:app \
    --host 0.0.0.0 \
    --port "${TOOL_API_PORT}" \
    --log-level warning &
TOOL_API_PID=$!

echo "==> Starting NeMo Agent Toolkit server on port 8000"
echo "==> Model: ${LLM_MODEL:-meta/llama-4-scout-17b-16e-instruct}"
echo "==> Display: ${DISPLAY}"

# Cleanup on exit
trap "kill ${XVFB_PID} ${TOOL_API_PID} 2>/dev/null; exit" INT TERM EXIT

exec nat serve --config_file workflow.yaml
