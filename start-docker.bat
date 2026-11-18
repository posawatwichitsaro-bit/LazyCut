@echo off
setlocal
cd /d "%~dp0"

docker compose up --build --detach --wait
if errorlevel 1 (
    echo LazyCut did not start. Make sure Docker Desktop is running with Linux containers.
    pause
    exit /b 1
)

for /f "tokens=*" %%A in ('docker compose port studio 8000') do start "" "http://%%A"
