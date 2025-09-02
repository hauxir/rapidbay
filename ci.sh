#!/bin/bash
set -e

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

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
echo "Running tests..."
python -m pytest tests/ -v

echo ""
echo "All checks passed!"