FROM ubuntu:24.04

# ---------- system deps ----------
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Display server
    xvfb \
    x11-utils \
    # Screenshot tools
    scrot \
    imagemagick \
    # Input automation
    xdotool \
    # Python (use distro default — 3.12 on Ubuntu 24.04)
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates \
    # Desktop apps for the agent to control
    xterm \
    && rm -rf /var/lib/apt/lists/*

# uv for fast Python installs
RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ---------- app ----------
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
COPY workflow.yaml ./

# Install into a venv (avoids --break-system-packages on Python 3.12)
ENV VIRTUAL_ENV=/app/.venv
RUN uv venv "$VIRTUAL_ENV" && uv pip install -e ".[all]"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# ---------- entrypoint ----------
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DISPLAY=:99
ENV DISPLAY_NUM=99
ENV COMPUTER_USE_PORT=8000
ENV COMPUTER_USE_HOST=0.0.0.0

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
