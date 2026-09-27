@echo off
title DX-Asset Development

cd /d "%~dp0"

echo ========================================
echo       DX-Asset Development Server
echo ========================================
echo.

echo [1/5] Starting PostgreSQL + Keycloak + SeaweedFS...
docker compose up -d postgres keycloak seaweedfs

if errorlevel 1 (
    echo.
    echo ERROR: Docker services failed to start.
    pause
    exit /b 1
)

echo.
echo Waiting for PostgreSQL + Keycloak...
ping 127.0.0.1 -n 6 >nul

echo.
echo [2/5] Running database migrations...
cd /d "%~dp0backend"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m alembic upgrade head
) else (
    python -m alembic upgrade head
)

if errorlevel 1 (
    echo.
    echo ERROR: Database migration failed.
    pause
    exit /b 1
)

echo.
echo [3/5] Starting Backend...
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
start "DX-Asset Backend" cmd /k "cd /d "%~dp0backend" && if exist .venv\Scripts\uvicorn.exe (.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000) else (uvicorn app.main:app --reload --port 8000)"

echo.
echo Waiting for Backend...
ping 127.0.0.1 -n 4 >nul

echo.
echo [4/5] Starting Frontend...
start "DX-Asset Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Waiting for Frontend...
ping 127.0.0.1 -n 6 >nul

echo.
echo ========================================
echo       DX-Asset Started
echo ========================================
echo.
echo PostgreSQL: Docker
echo Keycloak:   http://localhost:8080
echo Backend:    http://127.0.0.1:8000/docs
echo Frontend:   http://localhost:3000
echo.
echo ========================================

start http://localhost:3000

pause

