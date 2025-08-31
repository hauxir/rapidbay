#!/bin/bash
set -e

echo "Running basedpyright type checks..."
basedpyright app/

echo ""
echo "Running ruff linting..."
ruff check .

echo ""
echo "Running smoke test (import check)..."
cd app
python -c "import app; print('✓ app imports successfully')"
cd ..

echo ""
echo "All checks passed!"