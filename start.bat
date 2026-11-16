@echo off
setlocal enabledelayedexpansion
title LazyCut - AI Video Automation Studio

echo ==========================================================
echo        LazyCut - AI Video Automation Studio (Local)
echo ==========================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 2. Check or create virtual environment (.venv)
if not exist ".venv" (
    echo [*] Creating Python virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Activate virtual environment
call .venv\Scripts\activate

:: 4. Install / Update dependencies
echo [*] Checking dependencies in requirements.txt...
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Dependency installation returned an error. Continuing anyway...
)

:: 5. Launch browser in 3 seconds in background
echo [*] Launching LazyCut Studio at http://localhost:8000 ...
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"

:: 6. Run FastAPI Server
echo [*] Starting LazyCut Core Server...
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

pause
