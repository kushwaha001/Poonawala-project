#!/bin/bash
# ============================================================
#  Collateral Valuation Engine — One-Command Setup
#  Works on macOS, Linux, and WSL (Windows)
# ============================================================
set -e

echo ""
echo "============================================"
echo "  Collateral Valuation Engine — Setup"
echo "============================================"
echo ""

# Check Python version
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "ERROR: Python 3.8+ is required. Install from https://python.org"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "Python found: $PYTHON ($PY_VERSION)"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies (pinned versions for reproducibility)
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.lock.txt -q

# Copy .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

# Run tests
echo ""
echo "Running tests..."
python -m pytest tests/test_valuation_math.py -q
python tests/run_pipeline_test.py 2>&1 | tail -3
python tests/test_poonawala_fincorp.py 2>&1 | tail -3

echo ""
echo "============================================"
echo "  SETUP COMPLETE"
echo "============================================"
echo ""
echo "  To start the web app:"
echo ""
echo "    source venv/bin/activate"
echo "    python -m uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Then open: http://localhost:8000"
echo ""
echo "  To run tests:"
echo ""
echo "    python -m pytest tests/test_valuation_math.py -v"
echo "    python tests/run_pipeline_test.py"
echo "    python tests/test_poonawala_fincorp.py"
echo ""
