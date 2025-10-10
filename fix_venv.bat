@echo off
REM ============================================================================
REM Quick Fix Script - Recreate Virtual Environment and Install Dependencies
REM ============================================================================

echo.
echo ============================================================================
echo   FIX VIRTUAL ENVIRONMENT
echo ============================================================================
echo.

cd fastapi_backend

echo [1/4] Removing old virtual environment...
if exist "venv" (
    rmdir /s /q venv
    echo   - Old venv removed
) else (
    echo   - No existing venv found
)
echo.

echo [2/4] Creating fresh virtual environment...
pip install virtualenv
virtualenv venv

if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo.
    echo Try manually:
    echo   cd fastapi_backend
    echo   python -m venv venv
    pause
    exit /b 1
)
echo   - Virtual environment created successfully
echo.

echo [3/4] Installing build tools...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel

if errorlevel 1 (
    echo ERROR: Failed to install build tools
    pause
    exit /b 1
)
echo   - Build tools installed
echo.

echo [4/4] Installing dependencies...
echo.
echo Installing core packages first...
if exist "requirements_core.txt" (
    pip install -r requirements_core.txt
    echo   - Core packages installed
    echo.
)

echo Installing full requirements...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo WARNING: Some packages failed to install
    echo Attempting minimal installation...
    pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas openpyxl
)

echo.
echo ============================================================================
echo   TESTING INSTALLATION
echo ============================================================================
echo.

python -c "import fastapi; print('  - FastAPI: OK')"
python -c "import uvicorn; print('  - Uvicorn: OK')"
python -c "import sqlalchemy; print('  - SQLAlchemy: OK')"
python -c "import pandas; print('  - Pandas: OK')"

echo.
echo ============================================================================
echo   FIX COMPLETE
echo ============================================================================
echo.
echo You can now run:
echo   cd fastapi_backend
echo   call venv\Scripts\activate.bat
echo   python main.py
echo.
echo Or just run: start_all_single_window.bat
echo.

cd ..
pause

