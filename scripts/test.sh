#!/usr/bin/env bash
# Run tests for Hermes Computer Use
set -euo pipefail

echo "Running Hermes Computer Use tests..."
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing..."
    pip install pytest pytest-cov pytest-mock
fi

# Run tests with coverage
pytest \
    --cov=src/hermes_computer_use \
    --cov-report=term-missing \
    --cov-report=html \
    -v \
    "$@"

echo ""
echo "✓ Tests complete!"
