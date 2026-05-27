# hermes-computer-use — NeMo Agent Toolkit container
#
# Runs a react_agent with Ubuntu desktop automation tools served as an
# OpenAI-compatible /v1/chat/completions API on port 8000.
#
# Build:
#   docker build -t hermes-computer-use .
#
# Run (with a real X11 display):
#   docker run --rm -it \
#     -e DISPLAY=:1 \
#     -e NVIDIA_API_KEY=nvapi-... \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -p 8000:8000 \
#     hermes-computer-use
#
# Run (headless with Xvfb in the same container via docker-compose):
#   docker compose up

FROM python:3.11-slim

# ── System dependencies ──────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # X11 desktop automation
    xdotool \
    scrot \
    xauth \
    x11-apps \
    # Virtual display (headless mode)
    xvfb \
    xfce4 \
    xfce4-terminal \
    dbus-x11 \
    # Python build tools
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────────────────
WORKDIR /app

# Install NAT with LangChain support
RUN pip install --no-cache-dir \
    "nvidia-nat[langchain]>=1.7.0" \
    pyautogui \
    Pillow \
    python-xlib \
    requests

# Install our package
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[nat]"

# Copy workflow config
COPY workflow.yaml ./

# ── Entrypoint ───────────────────────────────────────────────────────────
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENV DISPLAY=:1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
