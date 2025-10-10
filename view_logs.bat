@echo off
REM ============================================================================
REM Log Viewer - View startup and server logs
REM ============================================================================

echo.
echo ============================================================================
echo   LOG VIEWER
echo ============================================================================
echo.

if not exist "logs" (
    echo No logs directory found
    echo Run start_all_single_window.bat first to generate logs
    pause
    exit /b 1
)

cd logs

REM Get latest log files
for /f "delims=" %%i in ('dir /b /o-d startup_*.log 2^>nul') do set "LATEST_STARTUP=%%i"
for /f "delims=" %%i in ('dir /b /o-d backend_install_*.log 2^>nul') do set "LATEST_BACKEND_INSTALL=%%i"
for /f "delims=" %%i in ('dir /b /o-d frontend_install_*.log 2^>nul') do set "LATEST_FRONTEND_INSTALL=%%i"
for /f "delims=" %%i in ('dir /b /o-d backend_server_*.log 2^>nul') do set "LATEST_BACKEND_SERVER=%%i"
for /f "delims=" %%i in ('dir /b /o-d frontend_server_*.log 2^>nul') do set "LATEST_FRONTEND_SERVER=%%i"

:menu
cls
echo.
echo ============================================================================
echo   LOG VIEWER - Select which log to view
echo ============================================================================
echo.
echo   INSTALLATION LOGS:
echo   1. Startup Log
echo   2. Backend Install Log
echo   3. Frontend Install Log
echo.
echo   SERVER RUNTIME LOGS (Real-time server output):
echo   4. Backend Server Log (All FastAPI output)
echo   5. Frontend Server Log (All Vite output)
echo.
echo   OTHER:
echo   6. View All Logs (Summary)
echo   7. List All Log Files
echo   8. Tail Backend Server (Live)
echo   9. Tail Frontend Server (Live)
echo   C. Clean Old Logs
echo   0. Exit
echo.
echo ============================================================================
echo.

set /p "CHOICE=Enter choice: "

if /i "%CHOICE%"=="1" goto :view_startup
if /i "%CHOICE%"=="2" goto :view_backend_install
if /i "%CHOICE%"=="3" goto :view_frontend_install
if /i "%CHOICE%"=="4" goto :view_backend_server
if /i "%CHOICE%"=="5" goto :view_frontend_server
if /i "%CHOICE%"=="6" goto :view_all
if /i "%CHOICE%"=="7" goto :list_logs
if /i "%CHOICE%"=="8" goto :tail_backend
if /i "%CHOICE%"=="9" goto :tail_frontend
if /i "%CHOICE%"=="C" goto :clean_logs
if /i "%CHOICE%"=="c" goto :clean_logs
if "%CHOICE%"=="0" goto :exit_viewer
goto :menu

:view_startup
cls
echo ============================================================================
echo   STARTUP LOG: %LATEST_STARTUP%
echo ============================================================================
echo.
if exist "%LATEST_STARTUP%" (
    type "%LATEST_STARTUP%"
) else (
    echo No startup log found
)
echo.
echo ============================================================================
pause
goto :menu

:view_backend_install
cls
echo ============================================================================
echo   BACKEND INSTALL LOG: %LATEST_BACKEND_INSTALL%
echo ============================================================================
echo.
if exist "%LATEST_BACKEND_INSTALL%" (
    type "%LATEST_BACKEND_INSTALL%"
) else (
    echo No backend install log found
)
echo.
echo ============================================================================
pause
goto :menu

:view_frontend_install
cls
echo ============================================================================
echo   FRONTEND INSTALL LOG: %LATEST_FRONTEND_INSTALL%
echo ============================================================================
echo.
if exist "%LATEST_FRONTEND_INSTALL%" (
    type "%LATEST_FRONTEND_INSTALL%"
) else (
    echo No frontend install log found
)
echo.
echo ============================================================================
pause
goto :menu

:view_backend_server
cls
echo ============================================================================
echo   BACKEND SERVER LOG: %LATEST_BACKEND_SERVER%
echo   (Showing last 100 lines - Server output can be very large)
echo ============================================================================
echo.
if exist "%LATEST_BACKEND_SERVER%" (
    powershell -Command "Get-Content '%LATEST_BACKEND_SERVER%' -Tail 100"
    echo.
    echo [Showing last 100 lines]
    echo Full log file: %CD%\%LATEST_BACKEND_SERVER%
) else (
    echo No backend server log found
    echo Server might still be starting or hasn't been run yet
)
echo.
echo ============================================================================
pause
goto :menu

:view_frontend_server
cls
echo ============================================================================
echo   FRONTEND SERVER LOG: %LATEST_FRONTEND_SERVER%
echo   (Showing last 100 lines - Server output can be very large)
echo ============================================================================
echo.
if exist "%LATEST_FRONTEND_SERVER%" (
    powershell -Command "Get-Content '%LATEST_FRONTEND_SERVER%' -Tail 100"
    echo.
    echo [Showing last 100 lines]
    echo Full log file: %CD%\%LATEST_FRONTEND_SERVER%
) else (
    echo No frontend server log found
    echo Server might still be starting or hasn't been run yet
)
echo.
echo ============================================================================
pause
goto :menu

:view_all
cls
echo ============================================================================
echo   ALL LOGS SUMMARY
echo ============================================================================
echo.

if exist "%LATEST_STARTUP%" (
    echo === STARTUP LOG ===
    type "%LATEST_STARTUP%"
    echo.
    echo.
)

if exist "%LATEST_BACKEND_INSTALL%" (
    echo === BACKEND INSTALL LOG (Last 30 lines) ===
    powershell -Command "Get-Content '%LATEST_BACKEND_INSTALL%' -Tail 30"
    echo.
    echo.
)

if exist "%LATEST_FRONTEND_INSTALL%" (
    echo === FRONTEND INSTALL LOG (Last 30 lines) ===
    powershell -Command "Get-Content '%LATEST_FRONTEND_INSTALL%' -Tail 30"
    echo.
    echo.
)

if exist "%LATEST_BACKEND_SERVER%" (
    echo === BACKEND SERVER LOG (Last 30 lines) ===
    powershell -Command "Get-Content '%LATEST_BACKEND_SERVER%' -Tail 30"
    echo.
    echo.
)

if exist "%LATEST_FRONTEND_SERVER%" (
    echo === FRONTEND SERVER LOG (Last 30 lines) ===
    powershell -Command "Get-Content '%LATEST_FRONTEND_SERVER%' -Tail 30"
    echo.
)

echo ============================================================================
pause
goto :menu

:tail_backend
cls
echo ============================================================================
echo   LIVE BACKEND SERVER LOG
echo   Press Ctrl+C to stop tailing
echo ============================================================================
echo.
if exist "%LATEST_BACKEND_SERVER%" (
    powershell -Command "Get-Content '%LATEST_BACKEND_SERVER%' -Wait -Tail 20"
) else (
    echo No backend server log found
    pause
)
goto :menu

:tail_frontend
cls
echo ============================================================================
echo   LIVE FRONTEND SERVER LOG
echo   Press Ctrl+C to stop tailing
echo ============================================================================
echo.
if exist "%LATEST_FRONTEND_SERVER%" (
    powershell -Command "Get-Content '%LATEST_FRONTEND_SERVER%' -Wait -Tail 20"
) else (
    echo No frontend server log found
    pause
)
goto :menu

:list_logs
cls
echo ============================================================================
echo   ALL LOG FILES
echo ============================================================================
echo.
echo STARTUP LOGS:
dir /b /od startup_*.log 2>nul
echo.
echo INSTALL LOGS:
dir /b /od *_install_*.log 2>nul
echo.
echo SERVER LOGS:
dir /b /od *_server_*.log 2>nul
echo.
if errorlevel 1 (
    echo No log files found
)
echo ============================================================================
pause
goto :menu

:clean_logs
cls
echo.
echo ============================================================================
echo   CLEAN OLD LOGS
echo ============================================================================
echo.
echo This will delete all logs except the most recent of each type.
echo.
echo Current log files:
dir /b *.log 2>nul | find /c /v "" 
echo total log files
echo.
set /p "CONFIRM=Type YES to confirm deletion: "

if /i "%CONFIRM%"=="YES" (
    echo.
    echo Cleaning old logs...
    
    REM Keep only the latest of each type
    for /f "skip=1 delims=" %%i in ('dir /b /o-d startup_*.log 2^>nul') do del "%%i" 2>nul
    for /f "skip=1 delims=" %%i in ('dir /b /o-d backend_install_*.log 2^>nul') do del "%%i" 2>nul
    for /f "skip=1 delims=" %%i in ('dir /b /o-d frontend_install_*.log 2^>nul') do del "%%i" 2>nul
    for /f "skip=1 delims=" %%i in ('dir /b /o-d backend_server_*.log 2^>nul') do del "%%i" 2>nul
    for /f "skip=1 delims=" %%i in ('dir /b /o-d frontend_server_*.log 2^>nul') do del "%%i" 2>nul
    
    echo.
    echo Old logs cleaned successfully
    echo Kept most recent log of each type
    echo.
    
    REM Show remaining files
    echo Remaining logs:
    dir /b *.log 2>nul
) else (
    echo.
    echo Cleanup cancelled
)
echo.
pause
goto :menu

:exit_viewer
cd ..
exit /b 0
