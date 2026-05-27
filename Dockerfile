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
    # Python
    python3.11 \
    python3-pip \
    python3.11-venv \
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

# Install with all optional extras
RUN uv pip install --system -e ".[all]"

# ---------- entrypoint ----------
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DISPLAY=:99
ENV DISPLAY_NUM=99
ENV COMPUTER_USE_PORT=8000
ENV COMPUTER_USE_HOST=0.0.0.0

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
