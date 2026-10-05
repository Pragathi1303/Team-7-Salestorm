@echo off
echo ============================================
echo  SALESTORM - Expiry Worker
echo ============================================

cd /d "%~dp0backend"
call .venv\Scripts\activate.bat

echo Starting reservation expiry worker...
python -m app.workers.expiry_worker
