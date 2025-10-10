@echo off
REM Startup script for Youcef Backend API
REM This script automatically handles database setup and starts the server

echo ========================================
echo Youcef Backend API Startup
echo ========================================
echo.

REM Check if we're in the correct directory
if not exist "fastapi_backend\main.py" (
    echo ERROR: Please run this script from the project root directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Change to backend directory
cd fastapi_backend

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo ✅ Python found

echo.
echo [2/3] Installing/updating dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies ready

echo.
echo [3/3] Starting FastAPI server...
echo.
echo The server will automatically:
echo   - Check PostgreSQL server connection
echo   - Create database if needed
echo   - Run Alembic migrations
echo   - Initialize tables and RBAC system
echo.
echo ========================================
echo.

REM Start the server
python main.py

REM If server stops, pause to see any error messages
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Server stopped with errors
    echo ========================================
    pause
)

