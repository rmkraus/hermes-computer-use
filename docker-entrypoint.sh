#!/bin/bash
# docker-entrypoint.sh — start display (if needed) then the NAT server
#
# Display selection (in priority order):
#   1. DISPLAY is set AND points to an accessible X server → use it as-is (host display)
#   2. DISPLAY is set but not accessible → start Xvfb on that display number
#   3. DISPLAY is unset → start Xvfb on :${DISPLAY_NUM:-1}
#
# Xauthority:
#   If XAUTHORITY is set and the file exists, it is exported before any X
#   connection attempt so the container can authenticate with the host X server.
#   The docker-compose.host-display.yaml overlay mounts the host Xauthority
#   to /tmp/.host-Xauthority and sets XAUTHORITY to that path.

set -e

SCREEN_RESOLUTION="${SCREEN_RESOLUTION:-1920x1080x24}"
XVFB_PID=""

# ── Xauthority setup ─────────────────────────────────────────────────────────
# Export XAUTHORITY if the file is present so libX11 can authenticate.
# Do this before the first xdpyinfo probe.
if [ -n "${XAUTHORITY:-}" ] && [ -f "${XAUTHORITY}" ]; then
    export XAUTHORITY
    echo "==> Using Xauthority: ${XAUTHORITY}"
elif [ -f "/tmp/.host-Xauthority" ] && [ -z "${XAUTHORITY:-}" ]; then
    # Fallback: docker-compose.host-display.yaml always mounts here
    export XAUTHORITY="/tmp/.host-Xauthority"
    echo "==> Using Xauthority: ${XAUTHORITY} (auto-detected)"
fi

# ── Display selection ────────────────────────────────────────────────────────
_display_accessible() {
    xdpyinfo -display "$1" >/dev/null 2>&1
}

if [ -n "${DISPLAY:-}" ] && _display_accessible "${DISPLAY}"; then
    echo "==> Using existing X display: ${DISPLAY}"
else
    # Determine which display number to start Xvfb on
    if [ -n "${DISPLAY:-}" ]; then
        # DISPLAY was set (e.g. :0) but not accessible — start Xvfb there
        DISPLAY_NUM="${DISPLAY#:}"
        DISPLAY_NUM="${DISPLAY_NUM%%.*}"   # strip screen suffix if any
    else
        DISPLAY_NUM="${DISPLAY_NUM:-1}"
    fi
    export DISPLAY=":${DISPLAY_NUM}"

    # When starting our own Xvfb, unset any host Xauthority — it won't work
    # for a new server and would cause confusing auth failures.
    unset XAUTHORITY

    echo "==> Starting Xvfb virtual display ${DISPLAY} at ${SCREEN_RESOLUTION}"
    Xvfb "${DISPLAY}" -screen 0 "${SCREEN_RESOLUTION}" &
    XVFB_PID=$!

    # Wait for Xvfb to be ready (up to 5 s)
    for i in $(seq 1 10); do
        if _display_accessible "${DISPLAY}"; then break; fi
        sleep 0.5
    done
    if ! _display_accessible "${DISPLAY}"; then
        echo "ERROR: Xvfb did not start on ${DISPLAY}" >&2
        exit 1
    fi
    echo "==> Xvfb ready on ${DISPLAY}"

    # Start a minimal window manager so windows can be focused/managed
    if command -v xfwm4 &>/dev/null; then
        echo "==> Starting xfwm4 window manager"
        xfwm4 --daemon --display "${DISPLAY}" 2>/dev/null || true
    fi
fi

# Allow X connections from all local clients (belt-and-suspenders for cases
# where xhost wasn't run on the host beforehand)
xhost +local: 2>/dev/null || true

# ── NAT server ───────────────────────────────────────────────────────────────
echo "==> Starting NeMo Agent Toolkit server on port 8000"
echo "    Model:   ${LLM_MODEL:-meta/llama-4-scout-17b-16e-instruct}"
echo "    Display: ${DISPLAY}"
echo "    Xauth:   ${XAUTHORITY:-<none>}"

# ── Cleanup ──────────────────────────────────────────────────────────────────
_cleanup() {
    echo "==> Shutting down..."
    [ -n "${XVFB_PID}" ] && kill "${XVFB_PID}" 2>/dev/null || true
}
trap _cleanup INT TERM EXIT

exec nat serve --config_file workflow.yaml
