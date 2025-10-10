@echo off
REM ============================================================================
REM Youcef Project - Complete Startup Script
REM Installs dependencies and launches both backend and frontend servers
REM ============================================================================

echo.
echo ============================================================================
echo   YOUCEF PROJECT - AUTOMATIC SETUP AND LAUNCH
echo ============================================================================
echo.

REM Check if we're in the correct directory
if not exist "fastapi_backend" (
    echo ERROR: fastapi_backend directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

if not exist "frontend" (
    echo ERROR: frontend directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
python --version
echo.

echo [2/4] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)
node --version
npm --version
echo.

REM ============================================================================
echo.
echo ============================================================================
echo   BACKEND SETUP (Virtual Environment)
echo ============================================================================
echo.

echo [Backend 1/3] Setting up Python virtual environment...
cd fastapi_backend

REM Check if venv exists
if exist "venv" (
    echo Virtual environment already exists
) else (
    echo Creating virtual environment...
    
    REM Try with virtualenv first (more reliable on Windows)
    pip install virtualenv >nul 2>&1
    virtualenv venv
    
    if errorlevel 1 (
        echo Virtualenv failed, trying with python -m venv...
        python -m venv venv --without-pip
        if errorlevel 1 (
            echo ERROR: Could not create virtual environment
            echo.
            echo Please try manually:
            echo   cd fastapi_backend
            echo   pip install virtualenv
            echo   virtualenv venv
            cd ..
            pause
            exit /b 1
        )
        echo Virtual environment created (without pip, will install after activation)
    ) else (
        echo Virtual environment created successfully
    )
)
echo.

echo [Backend 2/3] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    cd ..
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

echo [Backend 3/3] Installing Python dependencies in venv...

REM Install build dependencies first (critical!)
echo Installing build tools (pip, setuptools, wheel)...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo ERROR: Failed to install build dependencies
    cd ..
    pause
    exit /b 1
)
echo Build tools installed successfully
echo.

REM Install requirements
echo Installing application dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
    echo Continuing anyway...
)
echo Backend dependencies installed
cd ..
echo.

REM ============================================================================
echo.
echo ============================================================================
echo   FRONTEND SETUP
echo ============================================================================
echo.

echo [Frontend 1/2] Installing Node.js dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    cd ..
    pause
    exit /b 1
)
echo Frontend dependencies installed
cd ..
echo.

REM ============================================================================
echo.
echo ============================================================================
echo   LAUNCHING SERVERS
echo ============================================================================
echo.

echo Starting backend and frontend servers in separate windows...
echo.
echo Backend will run on: http://localhost:8001
echo Frontend will run on: http://localhost:5173
echo.
echo Press Ctrl+C in each window to stop the servers
echo.

REM Start backend in a new window (with venv activated)
start "Youcef Backend (FastAPI)" cmd /k "cd fastapi_backend && call venv\Scripts\activate.bat && python main.py"

REM Wait 3 seconds for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
start "Youcef Frontend (Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================================================
echo   SERVERS LAUNCHED!
echo ============================================================================
echo.
echo Backend: http://localhost:8001/docs
echo Frontend: http://localhost:5173
echo.
echo Two new windows have been opened:
echo   1. Youcef Backend (FastAPI)
echo   2. Youcef Frontend (Vite)
echo.
echo Close those windows or press Ctrl+C in them to stop the servers
echo.
echo ============================================================================
echo.

REM Keep this window open to show instructions
pause

