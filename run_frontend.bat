@echo off
echo ============================================
echo  SALESTORM - Frontend Setup
echo ============================================

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing npm packages...
    npm install
)

echo.
echo ============================================
echo  Starting SALESTORM frontend on port 3000
echo  Open: http://localhost:3000
echo  Admin: http://localhost:3000/admin
echo  Press Ctrl+C to stop
echo ============================================
echo.

npm run dev
