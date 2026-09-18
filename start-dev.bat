@echo off
title DX-Asset Development

cd /d D:\web\dx-asset

echo ========================================
echo       DX-Asset Development Server
echo ========================================
echo.

echo [1/3] Starting PostgreSQL...
docker compose up -d postgres

echo.
echo [2/3] Starting Backend...
start "DX-Asset Backend" cmd /k "cd /d D:\web\dx-asset\backend && .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"

echo.
echo [3/3] Starting Frontend...
start "DX-Asset Frontend" cmd /k "cd /d D:\web\dx-asset\frontend && npm run dev"

echo.
echo ========================================
echo PostgreSQL: Running through Docker
echo Backend:    http://127.0.0.1:8000/docs
echo Frontend:   http://localhost:3000
echo ========================================
echo.

timeout /t 5 /nobreak >nul
start http://localhost:3000

pause