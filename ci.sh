#!/bin/bash
set -e

echo "Running basedpyright type checks..."
basedpyright app/

echo ""
echo "Running ruff linting..."
ruff check .

echo ""
echo "All checks passed!"