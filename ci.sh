#!/bin/bash
set -e

echo "Running mypy type checks..."
mypy .

echo ""
echo "Running ruff linting..."
ruff check .

echo ""
echo "All checks passed!"