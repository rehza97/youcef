@echo off
REM ============================================================================
REM Safe Dependency Installation - Installs packages in small batches
REM Use this if normal installation crashes
REM ============================================================================

echo.
echo ============================================================================
echo   SAFE DEPENDENCY INSTALLATION
echo ============================================================================
echo.

cd fastapi_backend

REM Ensure venv exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    pip install virtualenv
    virtualenv venv
)

call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Install build tools
echo [1/8] Build Tools...
python -m pip install --upgrade pip setuptools wheel
echo   - Done
echo.

REM Install in batches to avoid crashes
echo [2/8] Core Framework...
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install python-multipart==0.0.6
echo   - Done
echo.

echo [3/8] Database...
pip install sqlalchemy==2.0.23
pip install alembic==1.12.1
pip install psycopg2-binary==2.9.9
echo   - Done
echo.

echo [4/8] Security...
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install cryptography==41.0.7
echo   - Done
echo.

echo [5/8] Configuration...
pip install pydantic==2.5.0
pip install pydantic-settings==2.1.0
pip install python-dotenv==1.0.0
pip install email-validator==2.1.0
echo   - Done
echo.

echo [6/8] Data Processing...
pip install numpy==1.26.4
pip install pandas==2.1.4
pip install openpyxl==3.1.2
echo   - Done
echo.

echo [7/8] File Handling & WebSockets...
pip install aiofiles==23.2.1
pip install websockets==12.0
pip install Pillow==10.0.1
echo   - Done
echo.

echo [8/8] Additional Utilities...
pip install redis==5.0.1
pip install python-email-validator==2.1.0
pip install pytz==2023.3
echo   - Done
echo.

echo ============================================================================
echo   VERIFICATION
echo ============================================================================
echo.

python -c "import fastapi; print('FastAPI: OK')"
python -c "import uvicorn; print('Uvicorn: OK')"
python -c "import sqlalchemy; print('SQLAlchemy: OK')"
python -c "import pandas; print('Pandas: OK')"
python -c "import openpyxl; print('OpenPyXL: OK')"

echo.
echo ============================================================================
echo   INSTALLATION COMPLETE
echo ============================================================================
echo.
echo All critical packages are installed!
echo.
echo You can now run:
echo   python main.py
echo.
echo Or exit this terminal and run:
echo   start_all_single_window.bat
echo.

cd ..
pause

