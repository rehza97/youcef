#!/bin/bash
# ============================================================================
# Youcef Project - Complete Startup Script (Linux/Mac)
# Installs dependencies and launches both backend and frontend servers
# ============================================================================

echo ""
echo "============================================================================"
echo "  YOUCEF PROJECT - AUTOMATIC SETUP AND LAUNCH"
echo "============================================================================"
echo ""

# Check if we're in the correct directory
if [ ! -d "fastapi_backend" ]; then
    echo "ERROR: fastapi_backend directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo "ERROR: frontend directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo "ERROR: Python is not installed or not in PATH"
    exit 1
fi

echo "[0/5] Updating from Git repository..."
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "WARNING: Git not found - skipping git update"
    echo ""
else
    # Check if this is a git repository
    if [ ! -d ".git" ]; then
        echo "WARNING: Not a git repository - using local files"
        echo ""
    else
        # Get current branch
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        echo "Current branch: $CURRENT_BRANCH"
        
        # Switch to fastapi_v1 if not already on it
        if [ "$CURRENT_BRANCH" != "fastapi_v1" ]; then
            echo "Switching to fastapi_v1 branch..."
            git checkout fastapi_v1
            if [ $? -ne 0 ]; then
                echo "WARNING: Could not switch to fastapi_v1 branch"
            fi
        fi
        
        # Fetch and pull latest changes
        echo "Fetching latest changes from origin/fastapi_v1..."
        git fetch origin fastapi_v1
        git pull origin fastapi_v1
        
        if [ $? -ne 0 ]; then
            echo "WARNING: Could not pull latest changes"
            read -p "Continue with current version? (y/n): " CONTINUE
            if [ "$CONTINUE" != "y" ]; then
                exit 1
            fi
        else
            echo "Repository updated successfully"
        fi
        echo ""
    fi
fi

echo "[1/5] Checking Python installation..."
$PYTHON_CMD --version
echo ""

echo "[2/5] Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH"
    exit 1
fi
node --version
npm --version
echo ""

# ============================================================================
echo ""
echo "============================================================================"
echo "  BACKEND SETUP (Virtual Environment)"
echo "============================================================================"
echo ""

echo "[Backend 1/3] Setting up Python virtual environment..."
cd fastapi_backend

# Check if venv exists
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    echo "Creating virtual environment..."
    
    # Try with virtualenv first (more reliable)
    $PIP_CMD install virtualenv >/dev/null 2>&1
    virtualenv venv
    
    if [ $? -ne 0 ]; then
        echo "Virtualenv failed, trying with python -m venv..."
        $PYTHON_CMD -m venv venv
        if [ $? -ne 0 ]; then
            echo "ERROR: Could not create virtual environment"
            echo ""
            echo "Please try manually:"
            echo "  cd fastapi_backend"
            echo "  $PIP_CMD install virtualenv"
            echo "  virtualenv venv"
            cd ..
            exit 1
        fi
        echo "Virtual environment created with venv module"
    else
        echo "Virtual environment created successfully"
    fi
fi
echo ""

echo "[Backend 2/3] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    cd ..
    exit 1
fi
echo "Virtual environment activated"
echo ""

echo "[Backend 3/3] Installing Python dependencies in venv..."

# Install build dependencies first (critical!)
echo "Installing build tools (pip, setuptools, wheel)..."
python -m pip install --upgrade pip setuptools wheel
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install build dependencies"
    cd ..
    exit 1
fi
echo "Build tools installed successfully"
echo ""

# Install requirements
echo "Installing application dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "WARNING: Some dependencies may have failed to install"
    echo "Continuing anyway..."
fi
echo "Backend dependencies installed"
cd ..
echo ""

# ============================================================================
echo ""
echo "============================================================================"
echo "  FRONTEND SETUP"
echo "============================================================================"
echo ""

echo "[Frontend 1/2] Installing Node.js dependencies..."
cd frontend
npm install
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install frontend dependencies"
    cd ..
    exit 1
fi
echo "Frontend dependencies installed"
cd ..
echo ""

# ============================================================================
echo ""
echo "============================================================================"
echo "  LAUNCHING SERVERS"
echo "============================================================================"
echo ""

echo "Starting backend and frontend servers..."
echo ""
echo "Backend will run on: http://localhost:8001"
echo "Frontend will run on: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Create a cleanup function
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Servers stopped"
    exit 0
}

# Set trap for cleanup on Ctrl+C
trap cleanup INT TERM

# Start backend in background (with venv activated)
cd fastapi_backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend in background
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================================================"
echo "  SERVERS LAUNCHED!"
echo "============================================================================"
echo ""
echo "Backend PID: $BACKEND_PID - http://localhost:8001/docs"
echo "Frontend PID: $FRONTEND_PID - http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "============================================================================"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID

