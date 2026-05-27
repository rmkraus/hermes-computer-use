#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-99}"
DISPLAY=":${DISPLAY_NUM}"
export DISPLAY

# Clean up stale X lock files from previous crashes
rm -f "/tmp/.X${DISPLAY_NUM}-lock"
rm -rf "/tmp/.X11-unix/X${DISPLAY_NUM}"

# Start virtual framebuffer
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

# Start the NAT server with the langgraph_wrapper workflow
exec nat serve --config_file /app/workflow.yaml
