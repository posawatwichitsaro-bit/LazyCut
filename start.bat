@echo off
cd /d "%~dp0"
title LazyCut Studio

echo ==========================================================
echo        LazyCut - AI Video Automation Studio (Local)
echo ==========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [*] Initializing virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
)

echo [*] Starting LazyCut Core Server at http://localhost:8000
echo [*] Press Ctrl+C in this window to stop the server.
echo.

start "" http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server terminated with error code %errorlevel%.
    pause
)
