@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM Youcef Project - Production-Ready Dual Window Startup
REM Launches backend and frontend in separate windows with full setup
REM Features: Virtual env, dependency install, error handling, health checks
REM ============================================================================

REM Configuration
set "PROJECT_NAME=YOUCEF PROJECT"
set "BACKEND_DIR=fastapi_backend"
set "FRONTEND_DIR=frontend"
set "VENV_DIR=venv"
set "BACKEND_PORT=8001"
set "FRONTEND_PORT=3000"
set "LOG_DIR=logs"
set "PYTHON_CMD=python"
set "MIN_PYTHON_VERSION=3.8"
set "MIN_NODE_VERSION=16"

REM Colors (Windows 10+ ANSI support)
set "COLOR_RESET=[0m"
set "COLOR_GREEN=[32m"
set "COLOR_YELLOW=[33m"
set "COLOR_RED=[31m"
set "COLOR_BLUE=[34m"
set "COLOR_CYAN=[36m"

REM Enable ANSI colors if supported
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%version%" geq "10.0" (
    reg query "HKCU\Console" /v VirtualTerminalLevel 2>nul | find "0x1" >nul
    if !errorlevel! equ 0 (
        set "ANSI_SUPPORTED=1"
    )
)

REM Header
cls
echo.
echo ============================================================================
echo   %COLOR_CYAN%%PROJECT_NAME% - PRODUCTION STARTUP%COLOR_RESET%
echo   Started at: %date% %time%
echo ============================================================================
echo.

REM Execute main startup sequence
goto :main_sequence

REM ============================================================================
REM Function: Check Prerequisites
REM ============================================================================
:check_prerequisites
echo [PREREQ] Checking prerequisites...
echo.

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%ERROR: Python not found in PATH%COLOR_RESET%
    echo Please install Python 3.8+ from https://www.python.org/
    goto :error_exit
)

REM Check Python version
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do (
    set PYTHON_VERSION=%%i
    for /f "tokens=1,2 delims=." %%a in ("%%i") do (
        set PY_MAJOR=%%a
        set PY_MINOR=%%b
    )
)

echo   - Python: %PYTHON_VERSION%
if !PY_MAJOR! LSS 3 (
    echo %COLOR_RED%ERROR: Python 3.8+ required, found !PY_MAJOR!.!PY_MINOR!%COLOR_RESET%
    goto :error_exit
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 8 (
    echo %COLOR_YELLOW%WARNING: Python 3.8+ recommended, found 3.!PY_MINOR!%COLOR_RESET%
)
echo     Status: %COLOR_GREEN%[OK]%COLOR_RESET%

REM Check pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%ERROR: pip not installed%COLOR_RESET%
    goto :error_exit
)
echo   - pip: %COLOR_GREEN%[OK]%COLOR_RESET%

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%ERROR: Node.js not found in PATH%COLOR_RESET%
    echo Please install Node.js from https://nodejs.org/
    goto :error_exit
)

REM Check Node version
for /f "tokens=1 delims=v" %%i in ('node --version 2^>^&1') do (
    set NODE_VERSION=%%i
    for /f "tokens=1 delims=." %%a in ("%%i") do set NODE_MAJOR=%%a
)

echo   - Node.js: v%NODE_VERSION%
if !NODE_MAJOR! LSS %MIN_NODE_VERSION% (
    echo %COLOR_YELLOW%WARNING: Node.js 16+ recommended, found !NODE_MAJOR!%COLOR_RESET%
)
echo     Status: %COLOR_GREEN%[OK]%COLOR_RESET%

REM Check npm
where npm >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%ERROR: npm not found%COLOR_RESET%
    goto :error_exit
)

for /f "tokens=1" %%i in ('npm --version 2^>^&1') do set NPM_VERSION=%%i
echo   - npm: %NPM_VERSION% %COLOR_GREEN%[OK]%COLOR_RESET%

echo.
goto :eof

REM ============================================================================
REM Step 1: Validate Directory Structure
REM ============================================================================
:validate_structure
echo [1/6] Validating project structure...
echo.

if not exist "%BACKEND_DIR%" (
    echo %COLOR_RED%ERROR: %BACKEND_DIR% directory not found%COLOR_RESET%
    echo Current directory: %CD%
    goto :error_exit
)
echo   - Backend directory: %COLOR_GREEN%[OK]%COLOR_RESET%

if not exist "%BACKEND_DIR%\main.py" (
    echo %COLOR_RED%ERROR: main.py not found in %BACKEND_DIR%%COLOR_RESET%
    goto :error_exit
)
echo   - main.py: %COLOR_GREEN%[OK]%COLOR_RESET%

if not exist "%FRONTEND_DIR%" (
    echo %COLOR_RED%ERROR: %FRONTEND_DIR% directory not found%COLOR_RESET%
    goto :error_exit
)
echo   - Frontend directory: %COLOR_GREEN%[OK]%COLOR_RESET%

if not exist "%BACKEND_DIR%\requirements.txt" (
    echo %COLOR_RED%ERROR: requirements.txt not found%COLOR_RESET%
    goto :error_exit
)
echo   - requirements.txt: %COLOR_GREEN%[OK]%COLOR_RESET%

if not exist "%FRONTEND_DIR%\package.json" (
    echo %COLOR_RED%ERROR: package.json not found in %FRONTEND_DIR%%COLOR_RESET%
    goto :error_exit
)
echo   - package.json: %COLOR_GREEN%[OK]%COLOR_RESET%

REM Create logs directory
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
    echo   - Created logs directory: %COLOR_GREEN%[OK]%COLOR_RESET%
)

echo.
goto :eof

REM ============================================================================
REM Step 2: Setup Python Virtual Environment
REM ============================================================================
:setup_venv
echo [2/6] Setting up Python virtual environment...
echo.
cd "%BACKEND_DIR%"

if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo   - Virtual environment exists: %COLOR_GREEN%[OK]%COLOR_RESET%
    echo   - Validating virtual environment...
    
    REM Validate venv by checking if it can activate
    call "%VENV_DIR%\Scripts\activate.bat" 2>nul
    if errorlevel 1 (
        echo %COLOR_YELLOW%WARNING: Existing venv is corrupted, recreating...%COLOR_RESET%
        rmdir /s /q "%VENV_DIR%" 2>nul
        goto :create_venv
    )
    call deactivate 2>nul
) else (
    :create_venv
    echo   - Creating virtual environment...
    
    REM Try python -m venv first (standard approach)
    %PYTHON_CMD% -m venv "%VENV_DIR%" 2>nul
    
    if errorlevel 1 (
        echo   - Standard venv failed, trying virtualenv...
        pip install virtualenv --quiet 2>nul
        virtualenv "%VENV_DIR%" 2>nul
        
        if errorlevel 1 (
            echo %COLOR_RED%ERROR: Could not create virtual environment%COLOR_RESET%
            echo.
            echo Troubleshooting steps:
            echo   1. cd %BACKEND_DIR%
            echo   2. python -m venv venv
            echo   OR
            echo   1. pip install virtualenv
            echo   2. virtualenv venv
            cd ..
            goto :error_exit
        )
    )
    
    echo   - Virtual environment created: %COLOR_GREEN%[OK]%COLOR_RESET%
)

echo.
goto :eof

REM ============================================================================
REM Step 3: Activate Virtual Environment and Install Dependencies
REM ============================================================================
:install_backend_deps
echo [3/6] Installing backend dependencies...
echo.

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo %COLOR_RED%ERROR: Failed to activate virtual environment%COLOR_RESET%
    cd ..
    goto :error_exit
)

echo   - Virtual environment activated: %COLOR_GREEN%[OK]%COLOR_RESET%
echo.

REM Install build dependencies first (critical!)
echo   - Installing build dependencies...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo %COLOR_RED%ERROR: Failed to install build dependencies%COLOR_RESET%
    echo.
    echo This is critical - cannot install other packages without setuptools
    echo.
    echo Try manually:
    echo   cd %BACKEND_DIR%
    echo   call venv\Scripts\activate.bat
    echo   python -m pip install --upgrade pip setuptools wheel
    cd ..
    goto :error_exit
)
echo     Build tools ready: %COLOR_GREEN%[OK]%COLOR_RESET%
echo.

REM Check if requirements files exist
if not exist "requirements.txt" (
    echo %COLOR_RED%ERROR: requirements.txt not found%COLOR_RESET%
    cd ..
    goto :error_exit
)

echo   - Installing Python packages...
echo     %COLOR_CYAN%This may take a few minutes on first run%COLOR_RESET%
echo.

REM Strategy: Try core packages first, then full requirements
echo   - Step 1: Installing core packages...

if exist "requirements_core.txt" (
    REM Try core packages first (more reliable)
    pip install -r requirements_core.txt
    
    if errorlevel 1 (
        echo %COLOR_RED%ERROR: Failed to install even core packages%COLOR_RESET%
        echo.
        echo Manual installation required:
        echo   pip install fastapi uvicorn sqlalchemy
        cd ..
        goto :error_exit
    )
    
    echo     Core packages installed: %COLOR_GREEN%[OK]%COLOR_RESET%
    echo.
    
    REM Now try full requirements
    echo   - Step 2: Installing additional packages...
    pip install -r requirements.txt 2>nul
    
    if errorlevel 1 (
        echo %COLOR_YELLOW%WARNING: Some optional packages failed%COLOR_RESET%
        echo %COLOR_CYAN%Continuing with core packages only%COLOR_RESET%
    ) else (
        echo     All packages installed: %COLOR_GREEN%[OK]%COLOR_RESET%
    )
) else (
    REM No core file, try full requirements directly
    pip install -r requirements.txt
    
    if errorlevel 1 (
        echo %COLOR_RED%ERROR: Package installation failed%COLOR_RESET%
        echo.
        echo Trying minimal installation...
        pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas
        
        if errorlevel 1 (
            echo %COLOR_RED%ERROR: Cannot install minimal packages%COLOR_RESET%
            cd ..
            goto :error_exit
        )
        echo %COLOR_CYAN%Minimal packages installed, continuing...%COLOR_RESET%
    )
)

echo.
echo   - Verifying critical packages...
python -c "import fastapi, uvicorn, sqlalchemy" 2>nul
if errorlevel 1 (
    echo %COLOR_RED%ERROR: Critical packages missing%COLOR_RESET%
    echo.
    echo Required packages not found. Please run:
    echo   cd %BACKEND_DIR%
    echo   call venv\Scripts\activate.bat
    echo   pip install fastapi uvicorn sqlalchemy
    cd ..
    goto :error_exit
)
echo     FastAPI, Uvicorn, SQLAlchemy: %COLOR_GREEN%[OK]%COLOR_RESET%

echo.
echo   - Backend dependencies ready: %COLOR_GREEN%[OK]%COLOR_RESET%

cd ..
echo.
goto :eof

REM ============================================================================
REM Step 4: Install Frontend Dependencies
REM ============================================================================
:install_frontend_deps
echo [4/6] Installing frontend dependencies...
echo.
cd "%FRONTEND_DIR%"

REM Check if node_modules exists and is valid
if exist "node_modules" (
    echo   - node_modules directory exists
    echo   - Checking if dependencies are up to date...
    echo.
    
    REM Check for package-lock.json changes
    call npm install --prefer-offline
) else (
    echo   - Installing fresh dependencies...
    echo     %COLOR_CYAN%This may take a few minutes on first run%COLOR_RESET%
    echo.
    call npm install
)

if errorlevel 1 (
    echo.
    echo %COLOR_RED%ERROR: npm install failed%COLOR_RESET%
    echo.
    echo Troubleshooting:
    echo   1. Check your internet connection
    echo   2. Delete node_modules and try again
    echo   3. Run: npm cache clean --force
    echo   4. Try: npm install --legacy-peer-deps
    cd ..
    goto :error_exit
)

echo.
echo   - Verifying installation...
if not exist "node_modules" (
    echo %COLOR_RED%ERROR: node_modules not created%COLOR_RESET%
    cd ..
    goto :error_exit
)

REM Count installed packages
for /f %%i in ('dir /b /a:d node_modules 2^>nul ^| find /c /v ""') do set PKG_COUNT=%%i
echo     Packages installed: %PKG_COUNT% %COLOR_GREEN%[OK]%COLOR_RESET%

echo   - Frontend dependencies ready: %COLOR_GREEN%[OK]%COLOR_RESET%

cd ..
echo.
goto :eof

REM ============================================================================
REM Step 5: Port Availability and Health Checks
REM ============================================================================
:check_ports
echo [5/6] Pre-flight checks...
echo.

echo   - Checking port availability...
netstat -ano | findstr ":%BACKEND_PORT%" >nul 2>&1
if not errorlevel 1 (
    echo     Backend port %BACKEND_PORT%: %COLOR_YELLOW%[IN USE]%COLOR_RESET%
    
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%"') do set PORT_PID=%%a
    echo     Process ID: !PORT_PID!
    
    set /p "KILL_PORT=Kill process and continue? (y/n): "
    if /i "!KILL_PORT!"=="y" (
        taskkill /F /PID !PORT_PID! >nul 2>&1
        timeout /t 2 /nobreak >nul
        echo     Process killed: %COLOR_GREEN%[OK]%COLOR_RESET%
    ) else (
        set /p "CONTINUE=Continue anyway? (y/n): "
        if /i not "!CONTINUE!"=="y" goto :error_exit
    )
) else (
    echo     Backend port %BACKEND_PORT%: %COLOR_GREEN%[Available]%COLOR_RESET%
)

netstat -ano | findstr ":%FRONTEND_PORT%" >nul 2>&1
if not errorlevel 1 (
    echo     Frontend port %FRONTEND_PORT%: %COLOR_YELLOW%[IN USE]%COLOR_RESET%
    
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%"') do set PORT_PID=%%a
    echo     Process ID: !PORT_PID!
    
    set /p "KILL_PORT=Kill process and continue? (y/n): "
    if /i "!KILL_PORT!"=="y" (
        taskkill /F /PID !PORT_PID! >nul 2>&1
        timeout /t 2 /nobreak >nul
        echo     Process killed: %COLOR_GREEN%[OK]%COLOR_RESET%
    ) else (
        set /p "CONTINUE=Continue anyway? (y/n): "
        if /i not "!CONTINUE!"=="y" goto :error_exit
    )
) else (
    echo     Frontend port %FRONTEND_PORT%: %COLOR_GREEN%[Available]%COLOR_RESET%
)

echo.
echo   - Checking disk space...
for /f "tokens=3" %%a in ('dir /-c ^| findstr "bytes free"') do set FREE_SPACE=%%a
echo     Available disk space: %FREE_SPACE% bytes

echo.
echo   - Pre-flight checks completed: %COLOR_GREEN%[OK]%COLOR_RESET%
echo.
goto :eof

REM ============================================================================
REM Step 6: Launch Servers in Separate Windows
REM ============================================================================
:start_servers
echo [6/6] Launching servers...
echo.

REM Start backend in new window
echo   - Starting backend server (FastAPI)...
start "Youcef Backend (FastAPI) - Port %BACKEND_PORT%" cmd /k "cd /d "%CD%\%BACKEND_DIR%" && call %VENV_DIR%\Scripts\activate.bat && title Youcef Backend - FastAPI && echo. && echo ============================================================================ && echo    YOUCEF BACKEND SERVER - FASTAPI && echo ============================================================================ && echo. && echo   Port: %BACKEND_PORT% && echo   API Documentation: http://localhost:%BACKEND_PORT%/docs && echo   ReDoc: http://localhost:%BACKEND_PORT%/redoc && echo   Health: http://localhost:%BACKEND_PORT%/health && echo. && echo   %COLOR_CYAN%Press Ctrl+C to stop the backend server%COLOR_RESET% && echo. && echo ============================================================================ && echo. && python main.py"

if errorlevel 1 (
    echo %COLOR_RED%ERROR: Failed to launch backend window%COLOR_RESET%
    goto :error_exit
)

echo     Backend window opened: %COLOR_GREEN%[OK]%COLOR_RESET%
echo     - URL: http://localhost:%BACKEND_PORT%
echo     - API Docs: http://localhost:%BACKEND_PORT%/docs
echo     - ReDoc: http://localhost:%BACKEND_PORT%/redoc
echo.

REM Wait for backend to initialize
echo   - Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

REM Start frontend in new window
echo   - Starting frontend server (Vite)...
start "Youcef Frontend (Vite) - Port %FRONTEND_PORT%" cmd /k "cd /d "%CD%\%FRONTEND_DIR%" && title Youcef Frontend - Vite && echo. && echo ============================================================================ && echo    YOUCEF FRONTEND SERVER - VITE && echo ============================================================================ && echo. && echo   Port: %FRONTEND_PORT% && echo   Local: http://localhost:%FRONTEND_PORT% && echo   Network: Check output below for network URL && echo. && echo   %COLOR_CYAN%Press Ctrl+C to stop the frontend server%COLOR_RESET% && echo. && echo ============================================================================ && echo. && npm run dev"

if errorlevel 1 (
    echo %COLOR_RED%ERROR: Failed to launch frontend window%COLOR_RESET%
    goto :error_exit
)

echo     Frontend window opened: %COLOR_GREEN%[OK]%COLOR_RESET%
echo     - URL: http://localhost:%FRONTEND_PORT%
echo.

REM Give servers time to fully start
timeout /t 3 /nobreak >nul

REM Final Success Screen
cls
echo.
echo ============================================================================
echo    %COLOR_GREEN%SERVERS SUCCESSFULLY LAUNCHED!%COLOR_RESET%
echo ============================================================================
echo.
echo   %COLOR_CYAN%Two separate windows have been opened:%COLOR_RESET%
echo.
echo   %COLOR_BLUE%1. BACKEND SERVER (FastAPI)%COLOR_RESET%
echo      - Main URL: http://localhost:%BACKEND_PORT%
echo      - API Docs: http://localhost:%BACKEND_PORT%/docs
echo      - ReDoc: http://localhost:%BACKEND_PORT%/redoc
echo      - Window Title: "Youcef Backend (FastAPI)"
echo.
echo   %COLOR_BLUE%2. FRONTEND SERVER (Vite)%COLOR_RESET%
echo      - Main URL: http://localhost:%FRONTEND_PORT%
echo      - Window Title: "Youcef Frontend (Vite)"
echo.
echo ============================================================================
echo   %COLOR_YELLOW%HOW TO STOP SERVERS:%COLOR_RESET%
echo ============================================================================
echo.
echo   Option 1: Close each window individually (click X)
echo   Option 2: Press Ctrl+C in each window
echo   Option 3: Run stop_servers.bat (if available)
echo.
echo ============================================================================
echo   %COLOR_CYAN%PROJECT INFORMATION:%COLOR_RESET%
echo ============================================================================
echo.
echo   Project: %PROJECT_NAME%
echo   Python: %PYTHON_VERSION%
echo   Node.js: v%NODE_VERSION%
echo   Logs: %LOG_DIR%\
echo   Started: %date% %time%
echo.
echo ============================================================================
echo   %COLOR_GREEN%TIPS:%COLOR_RESET%
echo ============================================================================
echo.
echo   - Keep this window open for reference
echo   - Check the server windows for real-time logs
echo   - Backend API docs provide interactive testing
echo   - Both servers auto-reload on file changes
echo.
echo ============================================================================
echo.

REM Keep this window open to show information
echo %COLOR_CYAN%Press any key to close this launcher window...%COLOR_RESET%
echo %COLOR_YELLOW%(Server windows will continue running)%COLOR_RESET%
echo.
pause >nul
goto :end_script

REM ============================================================================
REM Main Execution Sequence
REM ============================================================================
:main_sequence
call :check_prerequisites
call :validate_structure
call :setup_venv
call :install_backend_deps
call :install_frontend_deps
call :check_ports
call :start_servers
goto :eof

REM ============================================================================
REM Clean Exit
REM ============================================================================
:end_script
exit /b 0

REM ============================================================================
REM Error Exit Handler
REM ============================================================================
:error_exit
echo.
echo ============================================================================
echo   %COLOR_RED%STARTUP FAILED%COLOR_RESET%
echo ============================================================================
echo.
echo   Please review the error messages above and try again.
echo.
echo   Common solutions:
echo   - Ensure Python 3.8+ and Node.js 16+ are installed
echo   - Check your internet connection
echo   - Verify all required files exist
echo   - Try deleting venv and node_modules, then run again
echo.
echo   For support, check the project documentation or contact the team.
echo.
echo ============================================================================
echo.
pause
exit /b 1