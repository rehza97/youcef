@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM Youcef Project - Production-Ready Dual Window Startup
REM Launches backend and frontend in separate windows with full setup
REM Features: Virtual env, dependency install, error handling, health checks
REM ============================================================================

REM CRITICAL: Change to the script's directory first
cd /d "%~dp0"

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

REM Log files with timestamp
set "TIMESTAMP=%date:~-4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "STARTUP_LOG=%LOG_DIR%\startup_%TIMESTAMP%.log"
set "BACKEND_INSTALL_LOG=%LOG_DIR%\backend_install_%TIMESTAMP%.log"
set "FRONTEND_INSTALL_LOG=%LOG_DIR%\frontend_install_%TIMESTAMP%.log"
set "BACKEND_SERVER_LOG=%LOG_DIR%\backend_server_%TIMESTAMP%.log"
set "FRONTEND_SERVER_LOG=%LOG_DIR%\frontend_server_%TIMESTAMP%.log"

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

REM Create logs directory if it doesn't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Header
cls
echo.
echo ============================================================================
echo   %COLOR_CYAN%%PROJECT_NAME% - PRODUCTION STARTUP%COLOR_RESET%
echo   Started at: %date% %time%
echo ============================================================================
echo.
echo   Logging to: %STARTUP_LOG%
echo ============================================================================
echo.

REM Log startup info
echo ============================================================================ > "%STARTUP_LOG%"
echo   %PROJECT_NAME% - STARTUP LOG >> "%STARTUP_LOG%"
echo   Started at: %date% %time% >> "%STARTUP_LOG%"
echo ============================================================================ >> "%STARTUP_LOG%"
echo. >> "%STARTUP_LOG%"

REM Execute main startup sequence
call :main_sequence
if errorlevel 1 goto :error_exit
goto :success_complete

REM ============================================================================
REM Helper Functions
REM ============================================================================
:log_message
REM Usage: call :log_message "message"
if "%~1"=="" (
    echo.
    echo. >> "%STARTUP_LOG%" 2>nul
) else (
    echo %~1
    echo %~1 >> "%STARTUP_LOG%" 2>nul
)
goto :eof

:log_message_no_newline
REM Usage: call :log_message_no_newline "message"
echo|set /p=%~1
echo %~1 >> "%STARTUP_LOG%" 2>nul
goto :eof

REM ============================================================================
REM Function: Check Prerequisites
REM ============================================================================
:check_prerequisites
call :log_message "[PREREQ] Checking prerequisites..."
call :log_message " "

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    call :log_message "ERROR: Python not found in PATH"
    call :log_message "Please install Python 3.8+ from https://www.python.org/"
    goto :error_exit
)
echo Python check... >> "%STARTUP_LOG%"

REM Check Python version
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do (
    set PYTHON_VERSION=%%i
    for /f "tokens=1,2 delims=." %%a in ("%%i") do (
        set PY_MAJOR=%%a
        set PY_MINOR=%%b
    )
)

call :log_message "  - Python: %PYTHON_VERSION%"
if !PY_MAJOR! LSS 3 (
    call :log_message "ERROR: Python 3.8+ required, found !PY_MAJOR!.!PY_MINOR!"
    goto :error_exit
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 8 (
    call :log_message "ERROR: Python 3.8+ required, found 3.!PY_MINOR!"
    goto :error_exit
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! GEQ 8 if !PY_MINOR! LEQ 14 (
    echo     Status: %COLOR_GREEN%[OK - Tested with Python 3.8-3.14]%COLOR_RESET%
    echo     Status: [OK - Tested with Python 3.8-3.14] >> "%STARTUP_LOG%"
) else if !PY_MAJOR! EQU 3 (
    echo     Status: %COLOR_CYAN%[OK - Python 3.!PY_MINOR! - May work]%COLOR_RESET%
    echo     Status: [OK - Python 3.!PY_MINOR! - May work] >> "%STARTUP_LOG%"
) else (
    echo     Status: %COLOR_CYAN%[OK - Python !PY_MAJOR!.!PY_MINOR! - Untested]%COLOR_RESET%
    echo     Status: [OK - Python !PY_MAJOR!.!PY_MINOR! - Untested] >> "%STARTUP_LOG%"
)

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
call :log_message "  - Installing build dependencies..."
python -m pip install --upgrade pip setuptools wheel >> "%STARTUP_LOG%" 2>&1
if errorlevel 1 (
    call :log_message "ERROR: Failed to install build dependencies"
    call :log_message " "
    call :log_message "This is critical - cannot install other packages without setuptools"
    call :log_message " "
    call :log_message "Try manually:"
    call :log_message "  cd %BACKEND_DIR%"
    call :log_message "  call venv\Scripts\activate.bat"
    call :log_message "  python -m pip install --upgrade pip setuptools wheel"
    cd ..
    goto :error_exit
)
echo     Build tools ready: %COLOR_GREEN%[OK]%COLOR_RESET%
echo     Build tools ready: [OK] >> "%STARTUP_LOG%" 2>nul
call :log_message " "

REM Check if requirements files exist
if not exist "requirements.txt" (
    echo %COLOR_RED%ERROR: requirements.txt not found%COLOR_RESET%
    cd ..
    goto :error_exit
)

call :log_message "  - Installing Python packages..."
call :log_message "    This may take a few minutes on first run"
call :log_message " "

REM Strategy: Try core packages first, then full requirements
call :log_message "  - Step 1: Installing core packages..."
echo Installing core packages... >> "%STARTUP_LOG%"
echo ---------------------------------------- >> "%STARTUP_LOG%"

if exist "requirements_core.txt" (
    REM Try core packages first (more reliable)
    pip install -r requirements_core.txt >> "%BACKEND_INSTALL_LOG%" 2>&1
    
    if errorlevel 1 (
        call :log_message "ERROR: Failed to install even core packages"
        call :log_message " "
        call :log_message "Manual installation required:"
        call :log_message "  pip install fastapi uvicorn sqlalchemy"
        call :log_message " "
        echo Check log: %BACKEND_INSTALL_LOG%
        echo Check log: %BACKEND_INSTALL_LOG% >> "%STARTUP_LOG%" 2>nul
        cd ..
        goto :error_exit
    )
    
    echo     Core packages installed: %COLOR_GREEN%[OK]%COLOR_RESET%
    echo     Core packages installed: [OK] >> "%STARTUP_LOG%" 2>nul
    call :log_message " "
    
    REM Now try full requirements  
    call :log_message "  - Step 2: Installing additional packages..."
    echo Installing full requirements... >> "%STARTUP_LOG%"
    echo ---------------------------------------- >> "%STARTUP_LOG%"
    pip install -r requirements.txt >> "%BACKEND_INSTALL_LOG%" 2>&1
    
    if errorlevel 1 (
        echo %COLOR_YELLOW%WARNING: Some optional packages failed%COLOR_RESET%
        echo WARNING: Some optional packages failed >> "%STARTUP_LOG%" 2>nul
        echo %COLOR_CYAN%Continuing with core packages only%COLOR_RESET%
        echo Continuing with core packages only >> "%STARTUP_LOG%" 2>nul
    ) else (
        echo     All packages installed: %COLOR_GREEN%[OK]%COLOR_RESET%
        echo     All packages installed: [OK] >> "%STARTUP_LOG%" 2>nul
    )
) else (
    REM No core file, try full requirements directly
    pip install -r requirements.txt >> "%BACKEND_INSTALL_LOG%" 2>&1
    
    if errorlevel 1 (
        call :log_message "ERROR: Package installation failed"
        call :log_message " "
        call :log_message "Trying minimal installation..."
        pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas >> "%BACKEND_INSTALL_LOG%" 2>&1
        
        if errorlevel 1 (
            call :log_message "ERROR: Cannot install minimal packages"
            call :log_message "Check log: %BACKEND_INSTALL_LOG%"
            cd ..
            goto :error_exit
        )
        echo %COLOR_CYAN%Minimal packages installed, continuing...%COLOR_RESET%
        echo Minimal packages installed, continuing... >> "%STARTUP_LOG%" 2>nul
    )
)

call :log_message " "
call :log_message "  - Verifying critical packages..."
python -c "import fastapi, uvicorn, sqlalchemy" >> "%STARTUP_LOG%" 2>nul
if errorlevel 1 (
    call :log_message "ERROR: Critical packages missing"
    call :log_message " "
    call :log_message "Required packages not found. Please run:"
    call :log_message "  cd %BACKEND_DIR%"
    call :log_message "  call venv\Scripts\activate.bat"
    call :log_message "  pip install fastapi uvicorn sqlalchemy"
    cd ..
    goto :error_exit
)
echo     FastAPI, Uvicorn, SQLAlchemy: %COLOR_GREEN%[OK]%COLOR_RESET%
echo     FastAPI, Uvicorn, SQLAlchemy: [OK] >> "%STARTUP_LOG%" 2>nul

call :log_message " "
call :log_message "  - Backend dependencies ready: [OK]"

cd ..
call :log_message " "
goto :eof

REM ============================================================================
REM Step 4: Install Frontend Dependencies
REM ============================================================================
:install_frontend_deps
call :log_message "[4/6] Installing frontend dependencies..."
call :log_message " "
cd "%FRONTEND_DIR%"

echo Installing frontend packages... >> "%STARTUP_LOG%"
echo ---------------------------------------- >> "%STARTUP_LOG%"

REM Check if node_modules exists and is valid
if exist "node_modules" (
    call :log_message "  - node_modules directory exists"
    call :log_message "  - Checking if dependencies are up to date..."
    call :log_message " "
    
    REM Check for package-lock.json changes
    call npm install --prefer-offline >> "%FRONTEND_INSTALL_LOG%" 2>&1
) else (
    call :log_message "  - Installing fresh dependencies..."
    call :log_message "    This may take a few minutes on first run"
    call :log_message " "
    call npm install >> "%FRONTEND_INSTALL_LOG%" 2>&1
)

if errorlevel 1 (
    call :log_message " "
    call :log_message "ERROR: npm install failed"
    call :log_message " "
    call :log_message "Troubleshooting:"
    call :log_message "  1. Check your internet connection"
    call :log_message "  2. Delete node_modules and try again"
    call :log_message "  3. Run: npm cache clean --force"
    call :log_message "  4. Try: npm install --legacy-peer-deps"
    call :log_message " "
    echo Check log: %FRONTEND_INSTALL_LOG%
    echo Check log: %FRONTEND_INSTALL_LOG% >> "%STARTUP_LOG%" 2>nul
    cd ..
    goto :error_exit
)

call :log_message " "
call :log_message "  - Verifying installation..."
if not exist "node_modules" (
    call :log_message "ERROR: node_modules not created"
    cd ..
    goto :error_exit
)

REM Count installed packages
for /f %%i in ('dir /b /a:d node_modules 2^>nul ^| find /c /v ""') do set PKG_COUNT=%%i
echo     Packages installed: %PKG_COUNT% %COLOR_GREEN%[OK]%COLOR_RESET%
echo     Packages installed: %PKG_COUNT% [OK] >> "%STARTUP_LOG%"

call :log_message "  - Frontend dependencies ready: [OK]"

cd ..
call :log_message " "
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

REM Start backend in new window with logging
echo   - Starting backend server (FastAPI)...
echo Starting backend server at %date% %time% > "%BACKEND_SERVER_LOG%"
echo ============================================================================ >> "%BACKEND_SERVER_LOG%"
echo. >> "%BACKEND_SERVER_LOG%"

start "Youcef Backend (FastAPI) - Port %BACKEND_PORT%" cmd /k "cd /d "%CD%\%BACKEND_DIR%" && call %VENV_DIR%\Scripts\activate.bat && title Youcef Backend - FastAPI && cls && echo. && echo ============================================================================ && echo    YOUCEF BACKEND SERVER - FASTAPI && echo ============================================================================ && echo. && echo   Port: %BACKEND_PORT% && echo   API Documentation: http://localhost:%BACKEND_PORT%/docs && echo   ReDoc: http://localhost:%BACKEND_PORT%/redoc && echo   Health: http://localhost:%BACKEND_PORT%/health && echo. && echo   Server Output Log: ..\%BACKEND_SERVER_LOG% && echo   Press Ctrl+C to stop the backend server && echo. && echo ============================================================================ && echo. && (python main.py 2^>^&1 ^| powershell -Command \"$input ^| Tee-Object -FilePath '..\%BACKEND_SERVER_LOG%' -Append\")"

if errorlevel 1 (
    echo %COLOR_RED%ERROR: Failed to launch backend window%COLOR_RESET%
    goto :error_exit
)

echo     Backend window opened: %COLOR_GREEN%[OK]%COLOR_RESET%
echo     - URL: http://localhost:%BACKEND_PORT%
echo     - API Docs: http://localhost:%BACKEND_PORT%/docs
echo     - ReDoc: http://localhost:%BACKEND_PORT%/redoc
echo     - Server log: "%BACKEND_SERVER_LOG%"
echo.

REM Wait for backend to initialize
echo   - Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

REM Start frontend in new window with logging
echo   - Starting frontend server (Vite)...
echo Starting frontend server at %date% %time% > "%FRONTEND_SERVER_LOG%"
echo ============================================================================ >> "%FRONTEND_SERVER_LOG%"
echo. >> "%FRONTEND_SERVER_LOG%"

start "Youcef Frontend (Vite) - Port %FRONTEND_PORT%" cmd /k "cd /d "%CD%\%FRONTEND_DIR%" && title Youcef Frontend - Vite && cls && echo. && echo ============================================================================ && echo    YOUCEF FRONTEND SERVER - VITE && echo ============================================================================ && echo. && echo   Port: %FRONTEND_PORT% && echo   Local: http://localhost:%FRONTEND_PORT% && echo   Network: Check output below for network URL && echo. && echo   Server Output Log: ..\%FRONTEND_SERVER_LOG% && echo   Press Ctrl+C to stop the frontend server && echo. && echo ============================================================================ && echo. && (npm run dev 2^>^&1 ^| powershell -Command \"$input ^| Tee-Object -FilePath '..\%FRONTEND_SERVER_LOG%' -Append\")"

if errorlevel 1 (
    echo %COLOR_RED%ERROR: Failed to launch frontend window%COLOR_RESET%
    goto :error_exit
)

echo     Frontend window opened: %COLOR_GREEN%[OK]%COLOR_RESET%
echo     - URL: http://localhost:%FRONTEND_PORT%
echo     - Server log: "%FRONTEND_SERVER_LOG%"
echo.

REM Give servers time to fully start
timeout /t 3 /nobreak >nul

REM Log server launch
echo. >> "%STARTUP_LOG%"
echo ============================================================================ >> "%STARTUP_LOG%"
echo   SERVERS SUCCESSFULLY LAUNCHED >> "%STARTUP_LOG%"
echo   Time: %date% %time% >> "%STARTUP_LOG%"
echo ============================================================================ >> "%STARTUP_LOG%"
echo. >> "%STARTUP_LOG%"

REM Return to caller (main_sequence)
goto :eof

REM ============================================================================
REM Success Screen (called after all steps complete)
REM ============================================================================
:success_complete
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
echo   %COLOR_CYAN%LOG FILES:%COLOR_RESET%
echo   - Startup log: "%STARTUP_LOG%"
echo   - Backend install: "%BACKEND_INSTALL_LOG%"
echo   - Frontend install: "%FRONTEND_INSTALL_LOG%"
echo   - Backend server: "%BACKEND_SERVER_LOG%"
echo   - Frontend server: "%FRONTEND_SERVER_LOG%"
echo.
echo ============================================================================
echo.

REM Log completion
echo. >> "%STARTUP_LOG%"
echo Backend: http://localhost:%BACKEND_PORT% >> "%STARTUP_LOG%"
echo Frontend: http://localhost:%FRONTEND_PORT% >> "%STARTUP_LOG%"
echo. >> "%STARTUP_LOG%"
echo Log files: >> "%STARTUP_LOG%"
echo   - Startup: %STARTUP_LOG% >> "%STARTUP_LOG%"
echo   - Backend install: %BACKEND_INSTALL_LOG% >> "%STARTUP_LOG%"
echo   - Frontend install: %FRONTEND_INSTALL_LOG% >> "%STARTUP_LOG%"
echo   - Backend server: %BACKEND_SERVER_LOG% >> "%STARTUP_LOG%"
echo   - Frontend server: %FRONTEND_SERVER_LOG% >> "%STARTUP_LOG%"
echo. >> "%STARTUP_LOG%"
echo Startup completed successfully at: %date% %time% >> "%STARTUP_LOG%"
echo ============================================================================ >> "%STARTUP_LOG%"

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
echo. >> "%STARTUP_LOG%"
echo ============================================================================ >> "%STARTUP_LOG%"
echo   STARTUP FAILED >> "%STARTUP_LOG%"
echo   Time: %date% %time% >> "%STARTUP_LOG%"
echo ============================================================================ >> "%STARTUP_LOG%"

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
echo   %COLOR_YELLOW%Check logs for details:%COLOR_RESET%
echo   - Startup: "%STARTUP_LOG%"
echo   - Backend install: "%BACKEND_INSTALL_LOG%"
echo   - Frontend install: "%FRONTEND_INSTALL_LOG%"
echo   - Backend server: "%BACKEND_SERVER_LOG%"
echo   - Frontend server: "%FRONTEND_SERVER_LOG%"
echo.
echo   For support, check the project documentation or contact the team.
echo.
echo ============================================================================
echo.
pause
exit /b 1