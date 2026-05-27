"""Shared test fixtures and configuration."""

from __future__ import annotations

import io
import os
from unittest.mock import patch

import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables to prevent display errors."""
    with patch.dict(os.environ, {"DISPLAY": ":0"}):
        yield


@pytest.fixture
def sample_screenshot() -> bytes:
    """Generate a small sample PNG image for testing."""
    img = Image.new("RGB", (1920, 1080), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def small_screenshot() -> bytes:
    """Generate a smaller PNG for faster tests."""
    img = Image.new("RGB", (640, 480), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
