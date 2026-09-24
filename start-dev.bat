@echo off
title DX-Asset Development

cd /d D:\web\dx-asset

echo ========================================
echo       DX-Asset Development Server
echo ========================================
echo.

echo [1/5] Starting PostgreSQL...
docker compose up -d postgres

echo.
echo Waiting for PostgreSQL...
timeout /t 3 /nobreak >nul

echo.
echo [2/5] Running database migrations...
cd /d D:\web\dx-asset\backend
.venv\Scripts\python.exe -m alembic upgrade head

if errorlevel 1 (
    echo.
    echo ERROR: Database migration failed.
    pause
    exit /b 1
)

echo.
echo [3/5] Starting Backend...
start "DX-Asset Backend" cmd /k "cd /d D:\web\dx-asset\backend && .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"

echo.
echo Waiting for Backend...
timeout /t 3 /nobreak >nul

echo.
echo [4/5] Starting Frontend...
start "DX-Asset Frontend" cmd /k "cd /d D:\web\dx-asset\frontend && npm run dev"

echo.
echo Waiting for Frontend...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo       DX-Asset Started
echo ========================================
echo.
echo PostgreSQL: Docker
echo Backend:    http://127.0.0.1:8000/docs
echo Frontend:   http://localhost:3000
echo.
echo ========================================

start http://localhost:3000

pause