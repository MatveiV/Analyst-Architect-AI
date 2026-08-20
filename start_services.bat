@echo off
chcp 65001 >nul
cd /d C:\GitHub\3A

echo Stopping existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 "') do taskkill /f /pid %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting Backend (port 8000)...
wmic process call create "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000" >nul 2>&1

echo Starting Frontend (port 3000)...
wmic process call create "C:\GitHub\3A\frontend\run_vite.bat" >nul 2>&1

echo Waiting for services to start...
timeout /t 35 /nobreak >nul

echo.
echo ========================================
echo Service Status:
curl -s http://127.0.0.1:8000/health >nul 2>&1 && echo   BACKEND:  OK (port 8000) || echo   BACKEND:  DOWN
curl -s -o nul -w "  FRONTEND: HTTP %%{http_code} (port 3000)\n" http://127.0.0.1:3000
echo ========================================
