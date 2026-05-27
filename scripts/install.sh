#!/usr/bin/env bash
# Install system dependencies for Hermes Computer Use on Ubuntu
set -euo pipefail

echo "Installing system dependencies for Hermes Computer Use..."

# Package manager
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y \
        scrot \
        xdotool \
        imagemagick \
        x11-utils \
        x11-xserver-utils \
        xclip \
        xsel \
        libx11-dev \
        libxext-dev \
        libxi-dev \
        libxcursor-dev \
        libxdamage-dev \
        libxrandr-dev \
        python3-dev \
        python3-pip \
        python3-venv
    echo "✓ Installed Ubuntu/Debian dependencies"

elif command -v yum &> /dev/null; then
    sudo yum install -y \
        scrot \
        xdotool \
        ImageMagick \
        libX11-devel \
        libXext-devel \
        libXi-devel \
        libXcursor-devel \
        libXdamage-devel \
        libXrandr-devel
    echo "✓ Installed Fedora/RHEL dependencies"

elif command -v dnf &> /dev/null; then
    sudo dnf install -y \
        scrot \
        xdotool \
        ImageMagick \
        libX11-devel \
        libXext-devel \
        libXi-devel \
        libXcursor-devel \
        libXdamage-devel \
        libXrandr-devel
    echo "✓ Installed Fedora dependencies"

else
    echo "⚠ No supported package manager found. Install manually:"
    echo "  - scrot: screenshot capture"
    echo "  - xdotool: window management and input simulation"
    echo "  - imagemagick: image format conversion"
    echo "  - x11-utils: display utilities"
fi

echo ""
echo "Now install the Python package:"
echo "  pip install -e ."
echo ""
echo "Or use the install script:"
echo "  pip install -e '.[x11]'"
