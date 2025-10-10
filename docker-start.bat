@echo off
REM ============================================================================
REM Youcef Project - Docker Management Script (Windows)
REM Interactive menu with multiple commands support
REM ============================================================================

:init
cls
echo.
echo ============================================================================
echo   YOUCEF PROJECT - DOCKER MANAGEMENT
echo ============================================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo ✓ Docker is running
echo.

REM Check if docker-compose exists
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: docker-compose not found!
    echo.
    echo Please install Docker Compose and try again.
    echo.
    pause
    exit /b 1
)

echo ✓ docker-compose found
echo.

:menu
echo ============================================================================
echo   DOCKER COMMANDS MENU
echo ============================================================================
echo.
echo   [STARTUP OPTIONS]
echo   1. Fresh start (rebuild + start all)
echo   2. Quick start (start without rebuild)
echo   3. Start with auto-update from git
echo.
echo   [MANAGEMENT]
echo   4. Restart all containers
echo   5. Restart backend only
echo   6. Restart frontend only
echo   7. Restart database only
echo.
echo   [MONITORING]
echo   8. View all logs (live)
echo   9. View backend logs
echo   10. View frontend logs
echo   11. View database logs
echo   12. Show container status
echo.
echo   [MAINTENANCE]
echo   13. Stop all containers
echo   14. Stop and remove all (clean slate)
echo   15. Rebuild backend
echo   16. Rebuild frontend
echo   17. Rebuild all
echo.
echo   [DATABASE]
echo   18. Access PostgreSQL shell
echo   19. Backup database
echo   20. View database connections
echo.
echo   [SYSTEM]
echo   21. Clean Docker cache
echo   22. View Docker disk usage
echo   23. Run health checks
echo.
echo   0. Exit
echo.
echo ============================================================================
set /p choice="Enter your choice (0-23): "

if "%choice%"=="1" goto fresh_start
if "%choice%"=="2" goto quick_start
if "%choice%"=="3" goto auto_update_start
if "%choice%"=="4" goto restart_all
if "%choice%"=="5" goto restart_backend
if "%choice%"=="6" goto restart_frontend
if "%choice%"=="7" goto restart_database
if "%choice%"=="8" goto view_all_logs
if "%choice%"=="9" goto view_backend_logs
if "%choice%"=="10" goto view_frontend_logs
if "%choice%"=="11" goto view_database_logs
if "%choice%"=="12" goto show_status_only
if "%choice%"=="13" goto stop_containers
if "%choice%"=="14" goto clean_slate
if "%choice%"=="15" goto rebuild_backend
if "%choice%"=="16" goto rebuild_frontend
if "%choice%"=="17" goto rebuild_all
if "%choice%"=="18" goto postgres_shell
if "%choice%"=="19" goto backup_database
if "%choice%"=="20" goto view_db_connections
if "%choice%"=="21" goto clean_cache
if "%choice%"=="22" goto disk_usage
if "%choice%"=="23" goto health_check
if "%choice%"=="0" goto end
echo.
echo ❌ Invalid choice! Please enter a number between 0-23.
echo.
timeout /t 2 >nul
goto menu

REM ============================================================================
REM STARTUP OPTIONS
REM ============================================================================

:fresh_start
echo.
echo ============================================================================
echo   FRESH START - REBUILDING AND STARTING ALL CONTAINERS
echo ============================================================================
echo.
docker-compose down
docker-compose build --no-cache
docker-compose up -d
goto show_status

:quick_start
echo.
echo ============================================================================
echo   QUICK START - STARTING WITHOUT REBUILD
echo ============================================================================
echo.
docker-compose up -d
goto show_status

:auto_update_start
echo.
echo ============================================================================
echo   AUTO-UPDATE START - PULLING LATEST FROM GIT
echo ============================================================================
echo.
set AUTO_GIT_UPDATE=true
docker-compose down
docker-compose build
docker-compose up -d
goto show_status

REM ============================================================================
REM MANAGEMENT
REM ============================================================================

:restart_all
echo.
echo ============================================================================
echo   RESTARTING ALL CONTAINERS
echo ============================================================================
echo.
docker-compose restart
echo.
echo ✓ All containers restarted
echo.
pause
goto menu

:restart_backend
echo.
echo ============================================================================
echo   RESTARTING BACKEND CONTAINER
echo ============================================================================
echo.
docker-compose restart backend
echo.
echo ✓ Backend container restarted
echo.
pause
goto menu

:restart_frontend
echo.
echo ============================================================================
echo   RESTARTING FRONTEND CONTAINER
echo ============================================================================
echo.
docker-compose restart frontend
echo.
echo ✓ Frontend container restarted
echo.
pause
goto menu

:restart_database
echo.
echo ============================================================================
echo   RESTARTING DATABASE CONTAINER
echo ============================================================================
echo.
docker-compose restart postgres
echo.
echo ✓ Database container restarted
echo.
pause
goto menu

REM ============================================================================
REM MONITORING
REM ============================================================================

:view_all_logs
echo.
echo ============================================================================
echo   VIEWING ALL CONTAINER LOGS (Press Ctrl+C to exit)
echo ============================================================================
echo.
docker-compose logs --tail=50 --follow
goto menu

:view_backend_logs
echo.
echo ============================================================================
echo   VIEWING BACKEND LOGS (Press Ctrl+C to exit)
echo ============================================================================
echo.
docker-compose logs --tail=100 --follow backend
goto menu

:view_frontend_logs
echo.
echo ============================================================================
echo   VIEWING FRONTEND LOGS (Press Ctrl+C to exit)
echo ============================================================================
echo.
docker-compose logs --tail=100 --follow frontend
goto menu

:view_database_logs
echo.
echo ============================================================================
echo   VIEWING DATABASE LOGS (Press Ctrl+C to exit)
echo ============================================================================
echo.
docker-compose logs --tail=100 --follow postgres
goto menu

:show_status_only
echo.
echo ============================================================================
echo   CONTAINER STATUS
echo ============================================================================
echo.
docker-compose ps
echo.
echo ============================================================================
echo   DOCKER STATS
echo ============================================================================
echo.
docker stats --no-stream
echo.
pause
goto menu

REM ============================================================================
REM MAINTENANCE
REM ============================================================================

:stop_containers
echo.
echo ============================================================================
echo   STOPPING ALL CONTAINERS
echo ============================================================================
echo.
docker-compose stop
echo.
echo ✓ All containers stopped
echo.
pause
goto menu

:clean_slate
echo.
echo ⚠️  WARNING: This will remove all containers, networks, and volumes!
echo.
set /p confirm="Are you sure? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo.
    echo ❌ Operation cancelled
    echo.
    pause
    goto menu
)
echo.
echo ============================================================================
echo   CLEAN SLATE - REMOVING ALL CONTAINERS AND VOLUMES
echo ============================================================================
echo.
docker-compose down -v
echo.
echo ✓ Clean slate complete
echo.
pause
goto menu

:rebuild_backend
echo.
echo ============================================================================
echo   REBUILDING BACKEND CONTAINER
echo ============================================================================
echo.
docker-compose build --no-cache backend
docker-compose up -d backend
echo.
echo ✓ Backend rebuilt and restarted
echo.
pause
goto menu

:rebuild_frontend
echo.
echo ============================================================================
echo   REBUILDING FRONTEND CONTAINER
echo ============================================================================
echo.
docker-compose build --no-cache frontend
docker-compose up -d frontend
echo.
echo ✓ Frontend rebuilt and restarted
echo.
pause
goto menu

:rebuild_all
echo.
echo ============================================================================
echo   REBUILDING ALL CONTAINERS
echo ============================================================================
echo.
docker-compose build --no-cache
docker-compose up -d
echo.
echo ✓ All containers rebuilt and restarted
echo.
pause
goto menu

REM ============================================================================
REM DATABASE
REM ============================================================================

:postgres_shell
echo.
echo ============================================================================
echo   POSTGRESQL SHELL ACCESS
echo ============================================================================
echo.
echo Connecting to PostgreSQL... (Password: 123456789)
echo.
docker-compose exec postgres psql -U postgres -d youcef_db
echo.
pause
goto menu

:backup_database
echo.
echo ============================================================================
echo   DATABASE BACKUP
echo ============================================================================
echo.
set BACKUP_FILE=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql
set BACKUP_FILE=%BACKUP_FILE: =0%
echo Creating backup: %BACKUP_FILE%
echo.
docker-compose exec -T postgres pg_dump -U postgres youcef_db > %BACKUP_FILE%
echo.
echo ✓ Backup created: %BACKUP_FILE%
echo.
pause
goto menu

:view_db_connections
echo.
echo ============================================================================
echo   DATABASE CONNECTIONS
echo ============================================================================
echo.
docker-compose exec postgres psql -U postgres -d youcef_db -c "SELECT pid, usename, application_name, client_addr, state, query_start FROM pg_stat_activity WHERE datname = 'youcef_db';"
echo.
pause
goto menu

REM ============================================================================
REM SYSTEM
REM ============================================================================

:clean_cache
echo.
echo ============================================================================
echo   CLEANING DOCKER CACHE
echo ============================================================================
echo.
echo Removing unused images, containers, and networks...
echo.
docker system prune -f
echo.
echo ✓ Docker cache cleaned
echo.
pause
goto menu

:disk_usage
echo.
echo ============================================================================
echo   DOCKER DISK USAGE
echo ============================================================================
echo.
docker system df -v
echo.
pause
goto menu

:health_check
echo.
echo ============================================================================
echo   HEALTH CHECK
echo ============================================================================
echo.
echo [1/3] Checking PostgreSQL...
docker-compose exec postgres pg_isready -U postgres
echo.
echo [2/3] Checking Backend...
curl -s http://localhost:8001/health
echo.
echo.
echo [3/3] Checking Frontend...
curl -s -o nul -w "Frontend Status: %%{http_code}\n" http://localhost:3000
echo.
pause
goto menu

REM ============================================================================
REM STATUS DISPLAY
REM ============================================================================

:show_status
echo.
echo ============================================================================
echo   WAITING FOR SERVICES TO START
echo ============================================================================
echo.
timeout /t 10 /nobreak >nul

REM Check container status
docker-compose ps

echo.
echo ============================================================================
echo   YOUCEF PROJECT - RUNNING
echo ============================================================================
echo.
echo   PostgreSQL:  localhost:5432
echo   Backend:     http://localhost:8001
echo   API Docs:    http://localhost:8001/docs
echo   Frontend:    http://localhost:3000
echo.
echo ============================================================================
echo.
pause
goto menu

:end
echo.
echo ============================================================================
echo   EXITING DOCKER MANAGEMENT
echo ============================================================================
echo.
echo Goodbye!
echo.
timeout /t 2 >nul
exit /b 0

