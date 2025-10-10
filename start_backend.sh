#!/bin/bash
# Startup script for Youcef Backend API
# This script automatically handles database setup and starts the server

echo "========================================"
echo "Youcef Backend API Startup"
echo "========================================"
echo ""

# Check if we're in the correct directory
if [ ! -f "fastapi_backend/main.py" ]; then
    echo "ERROR: Please run this script from the project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Change to backend directory
cd fastapi_backend

echo "[1/3] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed or not in PATH"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD --version
echo "✅ Python found"

echo ""
echo "[2/3] Installing/updating dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi
echo "✅ Dependencies ready"

echo ""
echo "[3/3] Starting FastAPI server..."
echo ""
echo "The server will automatically:"
echo "  - Check PostgreSQL server connection"
echo "  - Create database if needed"
echo "  - Run Alembic migrations"
echo "  - Initialize tables and RBAC system"
echo ""
echo "========================================"
echo ""

# Start the server
$PYTHON_CMD main.py

# Check exit code
if [ $? -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "ERROR: Server stopped with errors"
    echo "========================================"
    exit 1
fi

