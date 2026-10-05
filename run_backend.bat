@echo off
echo ============================================
echo  SALESTORM - Local Development Setup
echo ============================================

cd /d "%~dp0backend"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt --quiet

echo Initializing database...
python -m app.core.init_db

echo.
echo ============================================
echo  Starting SALESTORM backend on port 8000
echo  API Docs: http://localhost:8000/docs
echo  Press Ctrl+C to stop
echo ============================================
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
